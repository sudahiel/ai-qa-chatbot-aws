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
- 使用 Ansible 進行自動化驗證（post-deploy smoke test）
- AWS 架構包含：
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
- 系統關鍵元件具備基礎監控與告警（Phase 7）

---

## 目前進度（Current Status）

### 環境資訊

- Pulumi Stack：dev
- AWS Region：ap-northeast-1（Tokyo）
- Backend Runtime：ECS Fargate

### 已確認資源（Pulumi Stack Outputs）

- S3 Bucket（assets）：ai-qa-chatbot-infra-dev-assets
- S3 Bucket（frontend）：ai-qa-chatbot-infra-dev-frontend
- ECR Repository：ai-qa-chatbot-infra-dev
- ECS Cluster：appCluster-5208a55
- ECS Service：backendService-2039b22
- ALB DNS：由 Pulumi 輸出取得
- CloudFront Domain：由 Pulumi 輸出取得

---

## Phase 2 – Backend on AWS（已完成）

### 架構摘要

- 使用 Pulumi 建立 ECS Fargate + ALB
- FastAPI（uvicorn）作為後端 API
- ALB 透過 Target Group（IP mode）將流量導向 ECS Task

### 健康檢查（Health Check）

- Endpoint：GET `/health`
- 預期回應：HTTP 200
- 狀態：Target Group 顯示為 Healthy（已驗證）

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

- POST `/api/chat`
- 特定問題（What time is it?）回傳 deterministic 結果
- 其他問題轉交 Amazon Bedrock（目前使用 Titan Text 系列模型）

---

## Phase 6 – Ansible Automation（已完成）

本專案導入 **Ansible 作為自動化驗證工具**，而非用於主機設定或 SSH 管理，  
而是專注於 **部署後（post-deploy）的產品入口驗證（smoke test）**。

### 設計重點

- Ansible 以 black-box 方式驗證系統
- 不需登入 AWS、不需 SSH、不需額外 IAM 權限
- 驗證對象為實際對外服務的 CloudFront 入口
- 以 ephemeral container 執行，避免污染本機環境

### Smoke Test 驗證項目

- CloudFront `/`
- CloudFront `/api/health`
- `/api/chat` deterministic path
- `/api/chat` Bedrock path

---

## Phase 6.5 – Post-deploy Smoke Test（CI 自動化）（已完成）

- Deploy workflow 成功後自動觸發 Ansible Smoke Test
- 由 GitHub Actions runner 執行
- 對 CloudFront 對外入口進行端到端驗證
- Smoke Test 失敗即視為 deploy 失敗（Release Gate）

---

## Phase 7 – Observability（已完成）

本階段導入 **最小可交付（Minimum Viable Observability）**，  
針對既有後端服務建立關鍵 CloudWatch 指標告警。

### 已實作告警（CloudWatch Alarms）

- ALB 5XX（ELB generated）
- Target Group Unhealthy（HealthyHostCount < 1）
- ECS CPU High（>= 80%, 3 minutes）
- ECS Memory High（>= 80%, 3 minutes）

所有告警皆由 Pulumi 管理，隨 stack 生命週期建立 / 更新 / 銷毀。

---

## Phase 8 – IAM Least Privilege（已完成）

### 背景與設計取捨

在專案初期，為了加速系統建置與驗證流程，  
CI 與基礎設施操作曾使用較寬鬆的 IAM 權限（例如直接使用 IAM User access key）。

當系統架構與部署流程穩定後，本階段針對 IAM 權限進行 **工程化收斂**，  
以符合實務上的 least-privilege 原則。

### 實作內容

本階段完成以下拆分與調整：

- **Infra 身分（人 / CLI / Pulumi）**
  - 僅用於基礎設施建置與管理
  - 與 CI / Runtime 身分分離

- **CI 身分（GitHub Actions）**
  - 改用 GitHub Actions OIDC 機制
  - 以 Assume Role 方式取得臨時憑證
  - 權限僅包含：
    - ECR image push
    - ECS task definition 註冊與 service 更新
    - 限定範圍的 `iam:PassRole`

- **Runtime 身分（ECS Task Role / Execution Role）**
  - Task Role 僅允許呼叫 Amazon Bedrock
  - Execution Role 僅負責 image pull、log 與 ECS Exec

### 成果

- CI 不再使用長期 access key
- CI / Infra / Runtime 身分與權限責任明確分離
- 系統仍維持完整 deploy / update / destroy 能力

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
- [x] Ansible-based smoke test
- [x] Observability (CloudWatch alarms)
- [x] IAM least-privilege hardening
- [ ] Bedrock model configuration refinement
- [ ] Production environment (prod stack)
