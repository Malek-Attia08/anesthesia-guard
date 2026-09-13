#!/usr/bin/env python3
"""
Model Optimization Script

Converts the trained PyTorch model to optimized formats:
- Dynamic Quantization (smaller, faster on CPU)
- TorchScript (JIT compiled)
- ONNX (best cross-platform performance)

Usage:
    python optimize_model.py --checkpoint models_raw/best_model_v13.pt --output_dir optimized_models
"""

import torch
import torch.nn as nn
import numpy as np
import copy
import time
import argparse
import warnings
from pathlib import Path
from typing import Dict, Any, Tuple

# Suppress warnings
warnings.filterwarnings('ignore')

# Import model architecture
import sys
sys.path.insert(0, str(Path(__file__).parent))
from app.models.emotion_model import (
    MultimodalEmotionModelV13, 
    MultimodalEmotionModelForONNX, 
    get_model_config
)


def load_trained_model(checkpoint_path: str, device: str = 'cpu') -> Tuple[nn.Module, Dict[str, Any]]:
    """Load the trained model from checkpoint"""
    print(f"Loading checkpoint: {checkpoint_path}")
    
    # PyTorch 2.6+ changed default weights_only=True
    try:
        checkpoint = torch.load(
            checkpoint_path, 
            map_location=device,
            weights_only=False
        )
    except TypeError:
        checkpoint = torch.load(checkpoint_path, map_location=device)
    
    # Get config from checkpoint or use default
    if 'config' in checkpoint:
        config = checkpoint['config']
        if isinstance(config.get('AUDIO_DIM'), str):
            config = get_model_config()
        default_config = get_model_config()
        for key in default_config:
            if key not in config:
                config[key] = default_config[key]
    else:
        config = get_model_config()
    
    print(f"   Config: AUDIO_HIDDEN={config.get('AUDIO_HIDDEN')}, VIT_HIDDEN={config.get('VIT_HIDDEN')}")
    
    # Create model
    model = MultimodalEmotionModelV13(config)
    
    # Load weights
    if 'model_state_dict' in checkpoint:
        model.load_state_dict(checkpoint['model_state_dict'])
    else:
        model.load_state_dict(checkpoint)
    
    model.eval()
    
    return model, config


def optimize_for_inference(model: nn.Module) -> nn.Module:
    """Apply basic inference optimizations"""
    model = copy.deepcopy(model)
    model.eval()
    
    # Disable dropout
    for module in model.modules():
        if isinstance(module, nn.Dropout):
            module.p = 0
    
    # Freeze parameters
    for param in model.parameters():
        param.requires_grad = False
    
    return model


def quantize_dynamic(model: nn.Module) -> nn.Module:
    """Apply dynamic quantization (CPU only)"""
    print("Applying dynamic quantization...")
    
    model_cpu = copy.deepcopy(model).cpu()
    model_cpu.eval()
    
    # Suppress deprecation warning
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        quantized = torch.quantization.quantize_dynamic(
            model_cpu,
            {nn.Linear, nn.LSTM},
            dtype=torch.qint8
        )
    
    return quantized


def export_to_torchscript(
    model: nn.Module, 
    save_path: str, 
    example_inputs: Tuple[torch.Tensor, ...]
) -> torch.jit.ScriptModule:
    """Export to TorchScript using tracing"""
    print(f"Exporting to TorchScript: {save_path}")
    
    model = copy.deepcopy(model)
    model.eval()
    
    # Wrap model to return tuple instead of dict
    class TracingWrapper(nn.Module):
        def __init__(self, base_model):
            super().__init__()
            self.model = base_model
            
        def forward(self, audio, vit, landmarks):
            out = self.model(audio, vit, landmarks)
            return (
                out['emotion'], 
                out['valence'], 
                out['arousal'], 
                out['int_ord']
            )
    
    wrapped = TracingWrapper(model)
    wrapped.eval()
    
    with torch.no_grad():
        traced = torch.jit.trace(wrapped, example_inputs)
    
    # Optimize for inference
    traced = torch.jit.optimize_for_inference(traced)
    
    # Save
    traced.save(save_path)
    print(f"✅ TorchScript saved: {save_path}")
    
    return traced


def export_to_onnx(
    model: nn.Module, 
    save_path: str, 
    example_inputs: Tuple[torch.Tensor, ...]
):
    """Export to ONNX format using legacy exporter"""
    try:
        import onnx
    except ImportError:
        print("   ⚠️ onnx not installed. Run: pip install onnx")
        return False
    
    print(f"Exporting to ONNX: {save_path}")
    
    # Wrap model for ONNX export
    wrapped = MultimodalEmotionModelForONNX(copy.deepcopy(model))
    wrapped.eval()
    
    audio, vit, landmarks = example_inputs
    
    # Use legacy exporter for better compatibility
    try:
        # Try legacy exporter first (more compatible)
        torch.onnx.export(
            wrapped,
            (audio, vit, landmarks),
            save_path,
            export_params=True,
            opset_version=17,  # Use higher opset for better compatibility
            do_constant_folding=True,
            input_names=['audio', 'vit', 'landmarks'],
            output_names=['emotion', 'valence', 'arousal', 'intensity'],
            dynamic_axes={
                'audio': {0: 'batch_size'},
                'vit': {0: 'batch_size'},
                'landmarks': {0: 'batch_size'},
                'emotion': {0: 'batch_size'},
                'valence': {0: 'batch_size'},
                'arousal': {0: 'batch_size'},
                'intensity': {0: 'batch_size'}
            },
            dynamo=False  # Use legacy exporter
        )
    except TypeError:
        # Older PyTorch without dynamo parameter
        torch.onnx.export(
            wrapped,
            (audio, vit, landmarks),
            save_path,
            export_params=True,
            opset_version=14,
            do_constant_folding=True,
            input_names=['audio', 'vit', 'landmarks'],
            output_names=['emotion', 'valence', 'arousal', 'intensity'],
            dynamic_axes={
                'audio': {0: 'batch_size'},
                'vit': {0: 'batch_size'},
                'landmarks': {0: 'batch_size'},
                'emotion': {0: 'batch_size'},
                'valence': {0: 'batch_size'},
                'arousal': {0: 'batch_size'},
                'intensity': {0: 'batch_size'}
            }
        )
    
    # Verify the exported model
    onnx_model = onnx.load(save_path)
    onnx.checker.check_model(onnx_model)
    
    print(f"✅ ONNX saved and verified: {save_path}")
    return True


def get_model_size_mb(model: nn.Module) -> float:
    """Calculate model size in MB"""
    param_size = sum(p.nelement() * p.element_size() for p in model.parameters())
    buffer_size = sum(b.nelement() * b.element_size() for b in model.buffers())
    return (param_size + buffer_size) / 1024 / 1024


def benchmark_pytorch_model(
    model: nn.Module, 
    example_inputs: Tuple[torch.Tensor, ...], 
    n_runs: int = 100,
    device: str = 'cpu'
) -> Dict[str, float]:
    """Benchmark PyTorch model inference speed"""
    model.eval()
    model.to(device)
    inputs = tuple(x.to(device) for x in example_inputs)
    
    # Warmup
    with torch.no_grad():
        for _ in range(10):
            _ = model(*inputs)
    
    if device == 'cuda':
        torch.cuda.synchronize()
    
    # Benchmark
    times = []
    with torch.no_grad():
        for _ in range(n_runs):
            start = time.perf_counter()
            _ = model(*inputs)
            if device == 'cuda':
                torch.cuda.synchronize()
            times.append(time.perf_counter() - start)
    
    return {
        'mean_ms': np.mean(times) * 1000,
        'std_ms': np.std(times) * 1000,
        'min_ms': np.min(times) * 1000,
        'max_ms': np.max(times) * 1000
    }


def benchmark_onnx(
    onnx_path: str, 
    example_inputs: Tuple[torch.Tensor, ...], 
    n_runs: int = 100
) -> Dict[str, float]:
    """Benchmark ONNX inference"""
    try:
        import onnxruntime as ort
    except ImportError:
        print("   ⚠️ onnxruntime not installed. Run: pip install onnxruntime")
        return None
    
    sess_options = ort.SessionOptions()
    sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    sess_options.intra_op_num_threads = 4
    sess_options.inter_op_num_threads = 4
    
    try:
        session = ort.InferenceSession(
            onnx_path, 
            sess_options=sess_options,
            providers=['CPUExecutionProvider']
        )
    except Exception as e:
        print(f"   ⚠️ Failed to load ONNX model: {e}")
        return None
    
    audio_np = example_inputs[0].numpy()
    vit_np = example_inputs[1].numpy()
    landmarks_np = example_inputs[2].numpy()
    
    # Warmup
    try:
        for _ in range(10):
            session.run(None, {
                'audio': audio_np, 
                'vit': vit_np, 
                'landmarks': landmarks_np
            })
    except Exception as e:
        print(f"   ⚠️ ONNX inference failed: {e}")
        return None
    
    # Benchmark
    times = []
    for _ in range(n_runs):
        start = time.perf_counter()
        session.run(None, {
            'audio': audio_np, 
            'vit': vit_np, 
            'landmarks': landmarks_np
        })
        times.append(time.perf_counter() - start)
    
    return {
        'mean_ms': np.mean(times) * 1000,
        'std_ms': np.std(times) * 1000,
        'min_ms': np.min(times) * 1000,
        'max_ms': np.max(times) * 1000
    }


def verify_model_output(
    model: nn.Module, 
    example_inputs: Tuple[torch.Tensor, ...]
):
    """Verify model produces expected output structure"""
    print("\nVerifying model output...")
    model.eval()
    
    with torch.no_grad():
        output = model(*example_inputs)
    
    if isinstance(output, dict):
        print("   Output type: Dictionary")
        print(f"   Keys: {list(output.keys())}")
        for key, value in output.items():
            if isinstance(value, torch.Tensor):
                print(f"   - {key}: shape={value.shape}, dtype={value.dtype}")
    elif isinstance(output, tuple):
        print("   Output type: Tuple")
        for i, value in enumerate(output):
            if isinstance(value, torch.Tensor):
                print(f"   - [{i}]: shape={value.shape}, dtype={value.dtype}")
    else:
        print(f"   Output type: {type(output)}")
    
    print("   ✅ Model output verified")


def main():
    parser = argparse.ArgumentParser(description='Optimize emotion recognition model')
    parser.add_argument('--checkpoint', type=str, required=True,
                        help='Path to trained model checkpoint')
    parser.add_argument('--output_dir', type=str, default='./optimized_models',
                        help='Output directory for optimized models')
    parser.add_argument('--device', type=str, default='cpu',
                        choices=['cpu', 'cuda'],
                        help='Device for benchmarking')
    parser.add_argument('--skip_onnx', action='store_true',
                        help='Skip ONNX export')
    parser.add_argument('--skip_torchscript', action='store_true',
                        help='Skip TorchScript export')
    parser.add_argument('--skip_quantize', action='store_true',
                        help='Skip quantization')
    parser.add_argument('--benchmark_runs', type=int, default=100,
                        help='Number of benchmark runs')
    args = parser.parse_args()
    
    output_dir = Path(args.output_dir)
    output_dir.mkdir(exist_ok=True, parents=True)
    
    print("=" * 60)
    print("MODEL OPTIMIZATION PIPELINE")
    print("=" * 60)
    
    # 1. Load model
    print("\n1. Loading trained model...")
    try:
        model, config = load_trained_model(args.checkpoint, args.device)
    except Exception as e:
        print(f"   ❌ Failed to load model: {e}")
        import traceback
        traceback.print_exc()
        return
    
    original_size = get_model_size_mb(model)
    num_params = sum(p.numel() for p in model.parameters())
    print(f"   Original size: {original_size:.2f} MB")
    print(f"   Parameters: {num_params:,}")
    
    # 2. Create example inputs
    print("\n2. Creating example inputs...")
    example_inputs = (
        torch.randn(1, 200, 1024),
        torch.randn(1, 32, 768),
        torch.randn(1, 32, 936)
    )
    print(f"   Audio: {example_inputs[0].shape}")
    print(f"   ViT: {example_inputs[1].shape}")
    print(f"   Landmarks: {example_inputs[2].shape}")
    
    verify_model_output(model, example_inputs)
    
    # 3. Benchmark original
    print("\n3. Benchmarking original model...")
    orig_bench = benchmark_pytorch_model(
        model, example_inputs, 
        n_runs=args.benchmark_runs, 
        device=args.device
    )
    print(f"   Latency: {orig_bench['mean_ms']:.2f} ± {orig_bench['std_ms']:.2f} ms")
    
    # 4. Optimize for inference
    print("\n4. Applying inference optimizations...")
    model_opt = optimize_for_inference(model)
    print("   ✅ Dropout disabled, parameters frozen")
    
    # 5. Dynamic quantization
    quant_bench = None
    quant_size = None
    
    if not args.skip_quantize:
        print("\n5. Applying dynamic quantization...")
        try:
            model_quant = quantize_dynamic(model_opt)
            quant_size = get_model_size_mb(model_quant)
            print(f"   Quantized size: {quant_size:.2f} MB ({quant_size/original_size*100:.1f}%)")
            
            quant_bench = benchmark_pytorch_model(
                model_quant, example_inputs, 
                n_runs=args.benchmark_runs, 
                device='cpu'
            )
            print(f"   Latency: {quant_bench['mean_ms']:.2f} ± {quant_bench['std_ms']:.2f} ms")
            
            # Save quantized model
            quant_path = output_dir / 'model_quantized.pt'
            torch.save({
                'model': model_quant, 
                'config': config
            }, quant_path)
            print(f"   ✅ Saved: {quant_path}")
            
        except Exception as e:
            print(f"   ⚠️ Quantization failed: {e}")
    else:
        print("\n5. Skipping quantization")
    
    # 6. TorchScript export
    script_bench = None
    
    if not args.skip_torchscript:
        print("\n6. Exporting to TorchScript...")
        try:
            script_path = output_dir / 'model_scripted.pt'
            model_scripted = export_to_torchscript(
                model_opt, 
                str(script_path),
                example_inputs
            )
            script_bench = benchmark_pytorch_model(
                model_scripted, example_inputs, 
                n_runs=args.benchmark_runs, 
                device=args.device
            )
            print(f"   Latency: {script_bench['mean_ms']:.2f} ± {script_bench['std_ms']:.2f} ms")
            
        except Exception as e:
            print(f"   ⚠️ TorchScript export failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n6. Skipping TorchScript export")
    
    # 7. ONNX export
    onnx_bench = None
    
    if not args.skip_onnx:
        print("\n7. Exporting to ONNX...")
        try:
            onnx_path = output_dir / 'model.onnx'
            
            # Clean up any existing ONNX files
            for f in output_dir.glob("model.onnx*"):
                f.unlink()
            
            success = export_to_onnx(model_opt, str(onnx_path), example_inputs)
            
            if success:
                onnx_bench = benchmark_onnx(
                    str(onnx_path), 
                    example_inputs,
                    n_runs=args.benchmark_runs
                )
                if onnx_bench:
                    print(f"   Latency: {onnx_bench['mean_ms']:.2f} ± {onnx_bench['std_ms']:.2f} ms")
                
        except Exception as e:
            print(f"   ⚠️ ONNX export failed: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\n7. Skipping ONNX export")
    
    # 8. Summary
    print("\n" + "=" * 60)
    print("OPTIMIZATION SUMMARY")
    print("=" * 60)
    print(f"{'Model':<20} {'Size (MB)':<12} {'Latency (ms)':<15} {'Speedup':<10}")
    print("-" * 60)
    print(f"{'Original':<20} {original_size:<12.2f} {orig_bench['mean_ms']:<15.2f} {'1.00x':<10}")
    
    if quant_bench and quant_size:
        speedup = orig_bench['mean_ms'] / quant_bench['mean_ms']
        print(f"{'Quantized':<20} {quant_size:<12.2f} {quant_bench['mean_ms']:<15.2f} {speedup:.2f}x")
    
    if script_bench:
        speedup = orig_bench['mean_ms'] / script_bench['mean_ms']
        print(f"{'TorchScript':<20} {'-':<12} {script_bench['mean_ms']:<15.2f} {speedup:.2f}x")
    
    if onnx_bench:
        speedup = orig_bench['mean_ms'] / onnx_bench['mean_ms']
        print(f"{'ONNX':<20} {'-':<12} {onnx_bench['mean_ms']:<15.2f} {speedup:.2f}x")
    
    print("=" * 60)
    
    # List generated files
    print(f"\n✅ Optimized models saved to: {output_dir}")
    print("\nGenerated files:")
    for f in output_dir.iterdir():
        size_mb = f.stat().st_size / 1024 / 1024
        print(f"   - {f.name}: {size_mb:.2f} MB")
    
    # Recommendations based on results
    print("\n📋 RECOMMENDATIONS:")
    
    # Determine best option
    best_option = "TorchScript"
    best_latency = script_bench['mean_ms'] if script_bench else float('inf')
    
    if onnx_bench and onnx_bench['mean_ms'] < best_latency:
        best_option = "ONNX"
        best_latency = onnx_bench['mean_ms']
    
    print(f"   ✨ Best option for your setup: {best_option} ({best_latency:.2f}ms)")
    print(f"   - Update INFERENCE_BACKEND in .env to: {best_option.lower()}")
    
    if quant_bench and quant_bench['mean_ms'] > orig_bench['mean_ms']:
        print("   ⚠️ Note: Quantization is slower on your CPU (common for small models)")


if __name__ == "__main__":
    main()