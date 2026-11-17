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

### Enterprise track

Real-life designs on more than one cloud: business story, architecture, sizing, HA/DR,
security, cost, a portal walkthrough, and Terraform + CI automation.

| # | Scenario | Status |
| --- | --- | --- |
| 09 | [Enterprise caching layer for AI: Azure Managed Redis + Google Memorystore for Valkey](scenarios/09-enterprise-ai-caching/) | Lab written, not yet run |

## Layout

```
scenarios/NN-name/
  README.md        step-by-step lab
  scripts/         numbered scripts, ending in a teardown
  sizing/          capacity math
  video/           slide source for the episode intro (render with Playwright + ffmpeg)
  docs/            portal walkthroughs, video plan, blog outline (enterprise track)
  terraform/       infrastructure as code, one folder per cloud (enterprise track)
```

## Ground rules

- One AWS account (and, for the enterprise track, one Azure subscription and one Google Cloud
  project) used only for these labs, each with a monthly budget alert.
- Every resource is tagged (or labeled) `project=ai-infra-series` and `scenario=NN`.
- Never commit keys, tokens or account IDs.
