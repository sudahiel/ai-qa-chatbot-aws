# AI Q&A Chatbot on AWS（工程導向練習專案，Work In Progress）

本專案為一個 **工程導向（Engineering-focused）** 的練習專案，目標是透過  
Infrastructure as Code（Pulumi）與 AWS 雲端原生服務，逐步建構一個  
**可部署、可更新、可完整銷毀（full lifecycle）** 的 AI 問答後端系統。

本專案刻意以「真實工程流程」推進，而非一次性完成所有功能。

> 📌 本 README 為「活文件（Living Document）」  
> 用來記錄目前已完成狀態、設計決策、工程取捨與下一步規劃，  
> 而非最終使用者操作手冊。

---

## 專案目標（Project Goals）

- 使用 Pulumi 管理 AWS 基礎設施（Infrastructure as Code）
- 建立可對外服務的後端 API（FastAPI）
- 導入並驗證 CI/CD 自動化部署流程
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
- 系統需支援完整生命週期（deploy / update / destroy）

> ⚠️ 本專案採用「分階段完成」方式，非所有元件一次完成。

---

## 高階架構概覽（High-Level Architecture）

### 已完成（Current）
- 使用者 / Client → ALB → ECS Fargate（FastAPI）
- Container image 儲存在 Amazon ECR
- 應用程式日誌輸出至 CloudWatch Logs

### 規劃中（Planned）
- CloudFront + S3 作為前端靜態網站
- Amazon Bedrock 提供 AI 問答能力
- Ansible 作為環境 bootstrap / 設定管理工具
- 強化 observability（metrics / alarms）

---

## 目前進度（Current Status）

### 環境資訊
- Pulumi Stack：`dev`
- AWS Region：`ap-northeast-1`（Tokyo）
- Backend Runtime：ECS Fargate
- Load Balancer：Application Load Balancer（ALB）

### 已確認資源（Pulumi Stack Outputs）
- S3 Bucket：`ai-qa-chatbot-infra-dev-assets`
- ECR Repository：`ai-qa-chatbot-infra-dev`
- ECS Cluster：`appCluster-05803ac`
- ECS Service：`backendService-c071a06`

---

## Phase 2 – Backend on AWS（已完成）

### 架構摘要
- 使用 Pulumi 建立 ECS Fargate + ALB
- FastAPI（uvicorn）作為後端 API
- ALB 透過 Target Group（IP mode）將流量導向 ECS Task

### 對外存取方式
- ALB DNS：`appAlb-d31e92c-1793100177.ap-northeast-1.elb.amazonaws.com`  
  （瀏覽器或 curl 請自行加上 `http://`）

### 健康檢查（Health Check）
- Endpoint：`GET /health`
- 預期回應：HTTP 200
- 狀態：Target Group 顯示為 `Healthy`（已驗證）

### 其他可用路徑
- Swagger UI：`GET /docs`
- OpenAPI Spec：`GET /openapi.json`

### 備註
- 根路徑 `GET /` 回傳 404 為預期行為（未實作 root route）
- 回應 header 出現 `server: uvicorn`，代表請求已成功到達後端服務

---

## Phase 3 – CI/CD Automation on ECS（已完成）

### 已完成的自動化流程
- 使用 GitHub Actions 建立 CI/CD pipeline
- 當程式碼 push 至 `master` 分支時，自動執行：
  1. Docker build backend image
  2. Image tag（`gitsha-<commit>` 與 `dev-latest`）
  3. Push image 至 Amazon ECR
  4. 註冊新的 ECS task definition revision
  5. 更新 ECS service，進行 rolling update

### 驗證方式
- ECR 中可看到對應 commit 的 image tag
- ECS running task 使用的 image 與最新 commit 一致
- 部署後 ALB `/health` 仍回傳 HTTP 200

### 後續優化方向
- IAM 權限由寬轉為 least privilege（將於 README 紀錄）
- 加入更明確的部署防護與環境區分機制

---

## Infrastructure Lifecycle（IaC）

所有 AWS 資源皆由 **Pulumi** 管理，支援完整生命週期：

- `pulumi preview`：預覽基礎設施變更
- `pulumi up`：建立或更新資源
- `pulumi destroy`：完整銷毀所有資源

此設計確保專案可在 **乾淨的 AWS 帳號中重複部署與移除**。

---

## IAM 與 Least Privilege（進行中）

### 目前狀態
- 開發初期使用較寬鬆的 IAM 權限
- 目標先驗證架構與部署流程正確性

### 規劃中的收斂方式
- 拆分 IAM Role（CI/CD、ECS Task、Infra）
- 僅保留實際所需的最小權限
- 在 README 中紀錄權限調整與設計理由

> 此做法貼近實務工程流程：  
> **先確保系統可運作，再逐步強化安全性**

---

## Observability（o11y）

### 目前
- 應用程式日誌：CloudWatch Logs
- 服務存活檢查：ALB Health Check

### 規劃中
- CloudWatch Metrics 與 Alarms
- 錯誤率與延遲監控
- （選擇性）Distributed tracing

---

## Roadmap（待完成事項）

- [x] ECS Fargate + ALB 後端架構
- [x] CI/CD 自動部署至 ECS
- [ ] CloudFront + S3 前端靜態網站
- [ ] Amazon Bedrock（AI Q&A 能力）
- [ ] Ansible playbook（設定與 bootstrap）
- [ ] IAM least-privilege 收斂與紀錄
- [ ] Observability 強化

---


## 備註

- 本專案仍在持續演進中
- README 會隨實作進度更新
