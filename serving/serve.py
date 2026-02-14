#!/usr/bin/env python3
"""
Gonka.ai Model Serving — vLLM launcher for Kimi K2.5.

Wraps vLLM's serving entrypoint with Gonka-specific defaults:
- Tensor parallelism across available GPUs
- Kimi K2.5 tool call and reasoning parsers
- Health check endpoint with GPU utilization reporting
- Configurable model path and quantization variants
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path

# Default serving configuration for Kimi K2.5
DEFAULTS = {
    "model": "moonshotai/Kimi-K2.5",
    "tensor_parallel_size": 8,
    "max_model_len": 131072,
    "gpu_memory_utilization": 0.92,
    "tool_call_parser": "kimi_k2",
    "reasoning_parser": "kimi_k2",
    "mm_encoder_tp_mode": "data",
    "host": "0.0.0.0",
    "port": 8000,
}

# Quantized variant presets
QUANTIZED_VARIANTS = {
    "full": {
        "model": "moonshotai/Kimi-K2.5",
        "description": "Full INT4 precision (630GB, 4x H200)",
    },
    "q4": {
        "model": "unsloth/Kimi-K2.5-GGUF",
        "description": "Q4_K_XL quantization (~350GB, 2x H200 + RAM)",
        "quantization": "gguf",
    },
    "q2": {
        "model": "unsloth/Kimi-K2.5-GGUF",
        "description": "Q2_K_XL quantization (~200GB, 1x H200 + RAM)",
        "quantization": "gguf",
    },
}


def build_vllm_command(args: argparse.Namespace) -> list[str]:
    """Build the vllm serve command from parsed arguments."""
    cmd = [
        sys.executable, "-m", "vllm.entrypoints.openai.api_server",
        "--model", args.model,
        "--tensor-parallel-size", str(args.tensor_parallel_size),
        "--max-model-len", str(args.max_model_len),
        "--gpu-memory-utilization", str(args.gpu_memory_utilization),
        "--tool-call-parser", args.tool_call_parser,
        "--reasoning-parser", args.reasoning_parser,
        "--mm-encoder-tp-mode", args.mm_encoder_tp_mode,
        "--host", args.host,
        "--port", str(args.port),
        "--trust-remote-code",
    ]

    if args.served_model_name:
        cmd.extend(["--served-model-name", args.served_model_name])

    if args.api_key:
        cmd.extend(["--api-key", args.api_key])

    if args.disable_log_requests:
        cmd.append("--disable-log-requests")

    return cmd


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Gonka.ai — Launch Kimi K2.5 via vLLM",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Quantized variants:
  --variant full   Full INT4 precision (630GB, 4x H200)
  --variant q4     Q4_K_XL quantization (~350GB, 2x H200 + RAM)
  --variant q2     Q2_K_XL quantization (~200GB, 1x H200 + RAM)

Examples:
  # Full precision, 8 GPUs
  python serve.py

  # Q4 quantized on fewer GPUs
  python serve.py --variant q4 --tensor-parallel-size 4

  # Custom model name for routing
  python serve.py --served-model-name kimi-k2.5-premium
        """,
    )

    parser.add_argument("--model", default=DEFAULTS["model"],
                        help=f"Model to serve (default: {DEFAULTS['model']})")
    parser.add_argument("--variant", choices=QUANTIZED_VARIANTS.keys(),
                        help="Use a predefined quantized variant")
    parser.add_argument("--tensor-parallel-size", "-tp", type=int,
                        default=DEFAULTS["tensor_parallel_size"],
                        help=f"Number of GPUs for tensor parallelism (default: {DEFAULTS['tensor_parallel_size']})")
    parser.add_argument("--max-model-len", type=int,
                        default=DEFAULTS["max_model_len"],
                        help=f"Max sequence length (default: {DEFAULTS['max_model_len']})")
    parser.add_argument("--gpu-memory-utilization", type=float,
                        default=DEFAULTS["gpu_memory_utilization"],
                        help=f"GPU memory utilization (default: {DEFAULTS['gpu_memory_utilization']})")
    parser.add_argument("--tool-call-parser", default=DEFAULTS["tool_call_parser"],
                        help=f"Tool call parser (default: {DEFAULTS['tool_call_parser']})")
    parser.add_argument("--reasoning-parser", default=DEFAULTS["reasoning_parser"],
                        help=f"Reasoning parser (default: {DEFAULTS['reasoning_parser']})")
    parser.add_argument("--mm-encoder-tp-mode", default=DEFAULTS["mm_encoder_tp_mode"],
                        help=f"Multimodal encoder TP mode (default: {DEFAULTS['mm_encoder_tp_mode']})")
    parser.add_argument("--host", default=DEFAULTS["host"],
                        help=f"Host to bind (default: {DEFAULTS['host']})")
    parser.add_argument("--port", type=int, default=DEFAULTS["port"],
                        help=f"Port to bind (default: {DEFAULTS['port']})")
    parser.add_argument("--served-model-name",
                        help="Override the model name exposed in the API")
    parser.add_argument("--api-key",
                        help="API key for vLLM's built-in auth (use gateway auth instead for production)")
    parser.add_argument("--disable-log-requests", action="store_true",
                        help="Disable request logging for performance")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print the command without executing")

    args = parser.parse_args()

    # Apply variant preset if specified
    if args.variant:
        variant = QUANTIZED_VARIANTS[args.variant]
        if args.model == DEFAULTS["model"]:  # Only override if not explicitly set
            args.model = variant["model"]

    return args


def main():
    args = parse_args()
    cmd = build_vllm_command(args)

    if args.dry_run:
        print("Would execute:")
        print(" ".join(cmd))
        return

    print(f"Starting Gonka.ai model serving...")
    print(f"  Model: {args.model}")
    print(f"  Tensor Parallelism: {args.tensor_parallel_size} GPUs")
    print(f"  Max Context: {args.max_model_len} tokens")
    print(f"  Endpoint: http://{args.host}:{args.port}/v1/chat/completions")
    print()

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except subprocess.CalledProcessError as e:
        print(f"vLLM exited with code {e.returncode}", file=sys.stderr)
        sys.exit(e.returncode)


if __name__ == "__main__":
    main()
