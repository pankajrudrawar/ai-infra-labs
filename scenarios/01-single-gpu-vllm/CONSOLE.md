# Scenario 01 in the AWS Console

The same lab as [README.md](README.md), done with clicks in the AWS Console instead of the AWS CLI.
The only commands you type run inside the instance, in a browser tab opened by Session Manager.

> Console labels move around. If a button name below doesn't match, look for the closest one.
> Use region **US East (N. Virginia) us-east-1** for every step (region picker, top right).

## 1. Prepare (once)

### 1.1 Check the GPU quota

1. Open **Service Quotas** → **AWS services** → **Amazon Elastic Compute Cloud (Amazon EC2)**.
2. Search for **Running On-Demand G and VT instances**.
3. **Applied account-level quota value** must be **8** or more. If your request is still pending, see
   **Quota request history** on the left. You can't launch a g6.xlarge (4 vCPUs) until it's approved.

### 1.2 Create a budget alert

1. Open **Billing and Cost Management** → **Budgets** → **Create budget**.
2. Choose **Use a template (simplified)** → **Monthly cost budget**.
3. Name it `ai-infra-labs`, set the amount to **$20**, enter your email, and **Create budget**.
   AWS emails you as spending approaches and passes the limit.

### 1.3 Create an IAM role for Session Manager

This lets you open a shell on the instance from the browser, with no SSH keys and no open ports.

1. Open **IAM** → **Roles** → **Create role**.
2. **Trusted entity type:** AWS service. **Use case:** EC2. → **Next**.
3. Search for and tick **AmazonSSMManagedInstanceCore** → **Next**.
4. **Role name:** `ai-infra-ssm-role` → **Create role**.

### 1.4 Get a Hugging Face token

1. Sign in at huggingface.co and open the
   [Llama 3.1 8B Instruct page](https://huggingface.co/meta-llama/Llama-3.1-8B-Instruct).
   Accept the license and wait for the approval email (often minutes, sometimes longer).
2. **Settings** → **Access Tokens** → **Create new token** → type **Read** → copy it somewhere safe.

## 2. Launch the GPU instance (billing starts here)

1. Open **EC2** → **Instances** → **Launch instances**.
2. **Name and tags:** name `scenario-01-vllm`. Click **Add additional tags** and add
   `project = ai-infra-series` and `scenario = 1`.
3. **Application and OS Images:** search for
   **Deep Learning Base OSS Nvidia Driver GPU AMI (Ubuntu 22.04)** and select the one whose
   provider is Amazon (verified). It comes with NVIDIA drivers, CUDA and Docker.
4. **Instance type:** `g6.xlarge`.
5. **Key pair:** **Proceed without a key pair** (Session Manager doesn't need one).
6. **Network settings** → **Edit**:
   - VPC: default. **Auto-assign public IP:** Enable (Session Manager needs outbound internet).
   - **Create security group**, and **remove** the SSH inbound rule so nothing is open to the internet.
7. **Configure storage:** **100** GiB, **gp3**.
8. **Advanced details** → **IAM instance profile:** `ai-infra-ssm-role`.
9. Check the **Summary** panel (1 × g6.xlarge), then **Launch instance**.

## 3. Connect and start vLLM

1. Wait until **Instance state** is Running and **Status check** shows 3/3 passed (2–5 minutes).
2. Select the instance → **Connect** → **Session Manager** tab → **Connect**. A shell opens in your browser.
   If Connect is greyed out, wait another minute; the agent needs time to register.
3. Switch to the default user and check the GPU:

   ```bash
   sudo su - ubuntu
   nvidia-smi          # NVIDIA L4, about 23 GB total, nothing running
   ```

4. Start vLLM (paste your token in place of `hf_xxx`):

   ```bash
   export HF_TOKEN=hf_xxx
   docker run -d --name vllm --gpus all --ipc=host -p 8000:8000 \
     -v ~/.cache/huggingface:/root/.cache/huggingface -e HF_TOKEN \
     vllm/vllm-openai:latest \
     --model meta-llama/Llama-3.1-8B-Instruct --served-model-name llm \
     --max-model-len 8192 --gpu-memory-utilization 0.90
   docker logs -f vllm     # wait for "Application startup complete", then Ctrl+C
   nvidia-smi              # memory used should match the napkin math
   ```

## 4. Test

```bash
curl -s localhost:8000/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "llm",
  "messages": [{"role": "user", "content": "Explain a GPU to a 10-year-old in two sentences."}]
}' | python3 -m json.tool
```

## 5. Benchmark

```bash
for C in 1 8 32; do
  docker exec vllm vllm bench serve --model meta-llama/Llama-3.1-8B-Instruct --served-model-name llm \
    --dataset-name random --random-input-len 512 --random-output-len 256 \
    --num-prompts 200 --max-concurrency $C
done
```

(Flag names change between vLLM versions: check `docker exec vllm vllm bench serve --help`.)

Then switch to the 4-bit model and repeat:

```bash
docker rm -f vllm
docker run -d --name vllm --gpus all --ipc=host -p 8000:8000 \
  -v ~/.cache/huggingface:/root/.cache/huggingface -e HF_TOKEN \
  vllm/vllm-openai:latest \
  --model hugging-quants/Meta-Llama-3.1-8B-Instruct-AWQ-INT4 --served-model-name llm \
  --max-model-len 8192 --gpu-memory-utilization 0.90
```

(In the benchmark loop, change `--model` to the 4-bit model name too.)

To watch the instance while it runs: select it in EC2 → **Monitoring** tab (CPU, network).
GPU memory and utilization come from `nvidia-smi` in the shell.

## 6. Tear down (do this the same day)

1. **EC2** → **Instances** → select `scenario-01-vllm` → **Instance state** → **Terminate (delete) instance**.
2. Wait for state **Terminated**.
3. **EC2** → **Volumes**: no 100 GiB volume should be left (it's deleted with the instance by default).
   Delete any that show **Available**.
4. Optional: **EC2** → **Security Groups** → delete the one the wizard created.
5. Next day: **Billing and Cost Management** → **Bills** to see what the lab actually cost.

Keep the IAM role and the budget; the next scenarios reuse them, and they cost nothing.
