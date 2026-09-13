import os
import gc
import json
import wave
import torch
import psutil
import tempfile
from fastapi import FastAPI, UploadFile, File, HTTPException
from pydub import AudioSegment
from vosk import Model, KaldiRecognizer
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
import uvicorn

#Configuration 
# Get the directory where main.py is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Now define paths relative to the project root (one level up from api/)
PROJECT_ROOT = os.path.dirname(BASE_DIR)

# Model paths (relative)
LOCAL_PATH = os.path.join(PROJECT_ROOT, "TunCHAT-V0.2")
VOSK_MODEL_DIR = os.path.join(PROJECT_ROOT, "vosk-model")

# Offload folder - you can keep it in system temp or make it relative too
OFFLOAD_DIR = os.path.join(PROJECT_ROOT, "tmp_offload")
os.makedirs(OFFLOAD_DIR, exist_ok=True)
SYSTEM_PROMPT = """
إنت طبيب مختص في التخدير ، جاوب على أسئلة المستعمل بطريقة بسيطة ومباشرة وباللهجة التونسية الدارجة فقط.

- جاوب باختصار، ما تطولش في الكلام
- إذا السؤال خارج مجال التخدير أو الطب، قل: "آسف، أنا مختص في التخدير فقط، ما نجمش نجاوب على هذا.
"""

#  Load Vosk model 
vosk_model = Model(VOSK_MODEL_DIR)

#  Memory setup 
cpu_mem_gb = psutil.virtual_memory().available / 1e9
cpu_mem_to_use = max(1, cpu_mem_gb * 0.7)

if torch.cuda.is_available():
    gpu_props = torch.cuda.get_device_properties(0)
    gpu_mem_total = gpu_props.total_memory / 1e9
    gpu_mem_reserved = torch.cuda.memory_reserved(0) / 1e9
    gpu_mem_free = gpu_mem_total - gpu_mem_reserved
    gpu_mem_to_use = max(0.5, gpu_mem_free * 0.8)
else:
    gpu_mem_to_use = 0

max_mem = {
    0: f"{gpu_mem_to_use:.2f}GB",
    "cpu": f"{cpu_mem_to_use:.2f}GB"
}
print(f"Using max_memory = {max_mem}")

#  Load LLM with 4-bit quantization 
print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(LOCAL_PATH)

print("Loading model (4-bit quantized)...")
quant_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_use_double_quant=True,
    bnb_4bit_compute_dtype=torch.float16
)

model = AutoModelForCausalLM.from_pretrained(
    LOCAL_PATH,
    quantization_config=quant_config,
    device_map="auto",
    max_memory=max_mem,
    offload_folder=OFFLOAD_DIR,
    dtype=torch.float16,
    low_cpu_mem_usage=True
)

print("Model loaded successfully!")

# Free memory after loading
gc.collect()
torch.cuda.empty_cache()

#  FastAPI app 
app = FastAPI(title="Tunisian Doctor Voice API")

@app.post("/process_audio/")
async def process_audio(audio_file: UploadFile = File(...)):
    m4a_path = None
    wav_path = None
    try:
        # Log incoming file
        print(f"Received file: {audio_file.filename} | Content-Type: {audio_file.content_type}")
        if not audio_file.filename.lower().endswith(('.m4a', '.wav', '.mp3', '.webm')):
            raise HTTPException(status_code=400, detail="Unsupported file format. Use .m4a, .wav, .mp3 or .webm")

        # Read file content
        file_content = await audio_file.read()

        # Create temp m4a
        with tempfile.NamedTemporaryFile(delete=False, suffix=".m4a") as temp_m4a:
            temp_m4a.write(file_content)
            m4a_path = temp_m4a.name
        print(f"Temp file created: {m4a_path}")

        # Convert to WAV
        audio = AudioSegment.from_file(m4a_path, format="m4a")
        audio = audio.set_channels(1).set_frame_rate(16000)
        wav_path = m4a_path.replace(".m4a", ".wav")
        audio.export(wav_path, format="wav")
        print(f"Conversion successful → WAV: {wav_path}")

        # Cleanup m4a early
        try:
            os.unlink(m4a_path)
        except:
            pass

        # Transcribe
        with wave.open(wav_path, "rb") as wf:
            if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getcomptype() != "NONE":
                raise ValueError("Audio must be mono 16-bit PCM WAV at 16000Hz")
           
            rec = KaldiRecognizer(vosk_model, wf.getframerate())
            rec.AcceptWaveform(wf.readframes(wf.getnframes()))
            result = json.loads(rec.FinalResult())
            transcript = result.get("text", "").strip()
            print(f"Transcription: '{transcript}'")

        # Cleanup WAV
        try:
            os.unlink(wav_path)
        except:
            pass

        if not transcript:
            return {"transcript": "", "response": "ما فهمتش سؤالك، ممكن تعاود؟"}

        #  LLM generation 
        # Use the exact same chat format as the model card
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ]

        # Apply the official chat template 
        formatted_prompt = tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True   # adds the assistant turn marker
        )
        print("Formatted prompt (chat template):\n", formatted_prompt)

        inputs = tokenizer(formatted_prompt, return_tensors="pt").to(model.device)
        print(f"Input token length: {inputs.input_ids.shape[1]}")
        print("Starting generation... Device:", model.device)

        try:
            with torch.no_grad():
                outputs = model.generate(
                    **inputs,
                    max_new_tokens=300,           # give it more room
                    temperature=0.7,
                    top_p=0.95,
                    do_sample=True,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                    repetition_penalty=1.1,
                )

            print("Generation finished. Output shape:", outputs.shape)

            # Decode full output
            full_text = tokenizer.decode(outputs[0], skip_special_tokens=True)

            # Extract only the assistant's new response
            if "assistant" in full_text.lower():
                # Take everything after the last "assistant"
                response = full_text.rsplit("assistant", 1)[-1].strip()
            elif "<start_of_turn>model" in full_text:
                response = full_text.split("<start_of_turn>model")[-1].strip()
            else:
                # Fallback: assume everything after the prompt is the answer
                response = full_text[len(formatted_prompt):].strip()  # remove input prompt length

            # Final cleanup
            response = response.lstrip(': \n').strip()

            print("Cleaned assistant response:", response)

            if not response or len(response) < 10:  # too short = generation failed
                response = "معليش، ما قدرتش نجاوب زين على السؤال هذا. ممكن توضح أكثر؟"

        except Exception as gen_err:
            print("Generation failed:", str(gen_err))
            import traceback
            traceback.print_exc()
            response = f"خطأ في التوليد: {str(gen_err)}"

        # Cleanup torch
        del inputs, outputs
        torch.cuda.empty_cache()
        gc.collect()

        return {
            "transcript": transcript,
            "response": response
        }

    except Exception as e:
        import traceback
        print("ERROR in /process_audio/:")
        traceback.print_exc()

        # Cleanup leftovers
        for path in [m4a_path, wav_path]:
            if path and os.path.exists(path):
                try:
                    os.unlink(path)
                except:
                    pass

        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "model_loaded": model is not None}

#  Run the server when script is executed directly 
if __name__ == "__main__":
    print("\nStarting FastAPI server...")
    print("Visit http://localhost:8005/docs to test the API\n")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8005,
        reload=False  # Set to True during development if you want auto-reload
    )