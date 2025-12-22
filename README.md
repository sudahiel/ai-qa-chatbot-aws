# AI Q&A Chatbot on AWS（工程導向練習專案，Work In Progress）

本專案為一個 **工程導向（Engineering-focused）** 的練習專案，目標是透過  
Infrastructure as Code（Pulumi）與 AWS 雲端原生服務，逐步建構一個  
**可部署、可更新、可完整銷毀（full lifecycle）** 的 AI 問答系統。

本專案刻意以「真實工程流程」推進，而非一次性完成所有功能。

> 📌 本 README 為「活文件（Living Document）」  
> 用來記錄目前已完成狀態、設計決策、工程取捨與下一步規劃，  
> 而非最終使用者操作手冊。

---

## 專案目標（Project Goals）

- 使用 Pulumi 管理 AWS 基礎設施（Infrastructure as Code）
- 建立可對外服務的後端 API（FastAPI）
- 導入並驗證 CI/CD 自動化部署流程
- 整合 Amazon Bedrock 提供 AI 問答能力
- 演進式收斂 IAM 權限（least privilege）
- 練習雲端系統的工程化建置與維運思維

---

## 與題目要求的對齊說明（Assignment Alignment）

本專案對齊以下題目要求進行設計與實作：

- 使用 Pulumi 進行 IaC 管理
- 使用 Ansible（規劃中）進行設定與自動化
- AWS 架構包含（已完成 / 規劃中）：
  - Application Load Balancer（ALB）
  - ECS Fargate
  - Amazon ECR
  - Amazon S3
  - CloudFront
  - Amazon Bedrock
- 關注重點：
  - IaC
  - CI/CD
  - Observability（o11y）
  - IAM least-privilege
- 系統支援完整生命週期（deploy / update / destroy）

---

## 高階架構概覽（High-Level Architecture）

### 已完成（Implemented）

- 使用者 / Browser  
  → CloudFront（HTTPS）
    - `/` → S3 靜態前端網站（Private Bucket + OAC）
    - `/api/*` → Application Load Balancer  
      → ECS Fargate（FastAPI）
- Container image 儲存在 Amazon ECR
- 後端服務整合 Amazon Bedrock（AI Q&A）
- 應用程式日誌輸出至 CloudWatch Logs

---

## 目前進度（Current Status）

### 環境資訊

- Pulumi Stack：`dev`
- AWS Region：`ap-northeast-1`（Tokyo）
- Backend Runtime：ECS Fargate

### 已確認資源（Pulumi Stack Outputs）

- S3 Bucket（assets）：`ai-qa-chatbot-infra-dev-assets`
- S3 Bucket（frontend）：`ai-qa-chatbot-infra-dev-frontend`
- ECR Repository：`ai-qa-chatbot-infra-dev`
- ECS Cluster：`appCluster-5208a55`
- ECS Service：`backendService-2039b22`
- ALB DNS：`appAlb-615a839-787066235.ap-northeast-1.elb.amazonaws.com`
- CloudFront Domain：`d1uufeos18qnvk.cloudfront.net`

**Demo 入口（HTTPS）：**  
https://d1uufeos18qnvk.cloudfront.net

---

## Phase 2 – Backend on AWS（已完成）

### 架構摘要

- 使用 Pulumi 建立 ECS Fargate + ALB
- FastAPI（uvicorn）作為後端 API
- ALB 透過 Target Group（IP mode）將流量導向 ECS Task

### 健康檢查（Health Check）

- Endpoint：`GET /health`
- 預期回應：HTTP 200
- 狀態：Target Group 顯示為 `Healthy`（已驗證）

---

## Phase 3 – CI/CD Automation on ECS（已完成）

- GitHub Actions 自動 build / push image 至 ECR
- 自動更新 ECS task definition 與 service
- Rolling update 後服務不中斷

---

## Phase 4 – Frontend on CloudFront + S3（已完成）

- S3 Private Bucket + CloudFront OAC
- `/` → 前端靜態頁面
- `/api/*` → ALB 後端 API
- 前後端同域，避免 mixed content 問題

---

## Phase 5 – Amazon Bedrock（AI Q&A）（已完成）

- `POST /api/chat`
- 特定問題（What time is it?）回傳 deterministic 結果
- 其他問題轉交 Amazon Bedrock（Titan Text Express）

---

## Phase 6 – Ansible（尚未完成）

- 規劃中：bootstrap / smoke test / automation

---

## Phase 7 – Observability（尚未完成）

- 規劃中：metrics、alarms、latency、error rate

---

## Phase 8 – IAM Least Privilege（尚未完成）

- 規劃中：
  - 拆分 Infra / Runtime / CI IAM Role
  - 收斂臨時放寬的權限
  - 在 README 中紀錄調整過程與理由

---

## Infrastructure Lifecycle（IaC）

- `pulumi preview`
- `pulumi up`
- `pulumi destroy`

---

## Roadmap

- [x] Backend on ECS + ALB
- [x] CI/CD automation
- [x] CloudFront + S3 frontend
- [x] Amazon Bedrock integration
- [ ] Ansible
- [ ] Observability
- [ ] IAM least-privilege hardening
