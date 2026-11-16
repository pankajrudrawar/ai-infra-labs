# ai-infra-labs

Hands-on AI infrastructure labs: GPU sizing, storage, Kubernetes for AI/ML, and reference architectures.
Each scenario is a working lab plus a YouTube episode and a Medium post.

> **Cost warning:** these labs create real cloud resources that bill by the hour. Every scenario
> ships a teardown script. Run it at the end of every session, and set an AWS Budget alert first.

## Scenarios

| # | Scenario | Status |
| --- | --- | --- |
| 01 | [Serve an LLM on one GPU and size it](scenarios/01-single-gpu-vllm/) | Lab written, not yet run |
| 02 | Distributed training on one multi-GPU node | Planned |
| 03 | Storage for training and inference | Planned |
| 04 | EKS with GPU nodes and the NVIDIA GPU Operator | Planned |
| 05 | Production model serving with vLLM and KServe | Planned |
| 06 | Distributed training and pipelines with Ray or Kubeflow | Planned |
| 07 | Reference architecture: an end-to-end RAG platform | Planned |
| 08 | Managed platforms vs. DIY (SageMaker, Bedrock, Azure, GPU clouds) | Planned |

## Layout

```
scenarios/NN-name/
  README.md        step-by-step lab
  scripts/         numbered scripts, ending in a teardown
  sizing/          capacity math
  video/           slide source for the episode intro (render with Playwright + ffmpeg)
```

## Ground rules

- One AWS account used only for these labs, with a monthly budget alert.
- Every resource is tagged `project=ai-infra-series` and `scenario=NN`.
- Never commit keys, tokens or account IDs.
