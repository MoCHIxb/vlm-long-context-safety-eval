"""Select the Qwen3-only RTX3090 profile without changing the LLaVA/Gemma default."""
from cloud_runtime_rtx3090 import main


if __name__ == '__main__':
    main('configs/cloud/rtx3090_qwen3.json')
