# AI Q&A Chatbot on AWS（工程導向練習專案，Work In Progress）

本專案為一個 **工程導向（Engineering-focused）** 的練習專案，  
目標是透過 Infrastructure as Code（Pulumi）與 AWS 雲端原生服務，  
逐步建構一個 **可部署、可更新、可完整銷毀（full lifecycle）** 的 AI 問答系統。

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

使用者 / Browser  
→ CloudFront（HTTPS）

- `/`  
  → S3 靜態前端網站（Private Bucket + Origin Access Control）

- `/api/*`  
  → Application Load Balancer  
  → ECS Fargate（FastAPI）  
  → Amazon Bedrock（Nova model via inference profile）

其他元件：

- Container image 儲存在 Amazon ECR
- 應用程式日誌輸出至 CloudWatch Logs
- 關鍵服務具備基礎監控與告警（Phase 7）

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
- ECS Cluster：會隨 stack recreate 變動
- ECS Service：會隨 stack recreate 變動
- ALB DNS：會隨 stack recreate 變動
- CloudFront Domain：會隨 stack recreate 變動

查詢指令（建議在 repo 根目錄執行）
cd infra

# ECS
pulumi stack output ecs_cluster_name
pulumi stack output ecs_service_name

# Entry points
pulumi stack output alb_dns_name
pulumi stack output cloudfront_domain_name

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
- 自動註冊 ECS task definition 並更新 service
- Rolling update 過程中服務不中斷
- CI 與 Runtime IAM 身分分離

---

## Phase 4 – Frontend on CloudFront + S3（已完成）

- S3 Private Bucket + CloudFront OAC
- `/` → 前端靜態頁面
- `/api/*` → ALB 後端 API
- 前後端同域，避免 mixed content 問題

---

## Phase 5 – Amazon Bedrock（AI Q&A）（已完成）

- POST `/api/chat`
- deterministic path：
  - 特定問題（例如時間查詢）由後端直接處理
- AI inference path：
  - 透過 Amazon Bedrock 呼叫 Nova model
  - 使用 inference profile（非 on-demand model ID）
- Bedrock 呼叫權限僅存在於 ECS Task Role

---

## Phase 6 – Ansible Automation（已完成）

本專案導入 **Ansible 作為自動化驗證工具**，  
用途為部署完成後的 **黑箱驗證（post-deploy smoke test）**，  
而非主機設定或 SSH 管理。

### 設計重點

- 不需登入 AWS
- 不需 SSH
- 不需額外 IAM 權限
- 驗證對象為實際對外服務（CloudFront）
- 以 ephemeral runner 執行，避免污染本機環境

### Smoke Test 驗證項目

- CloudFront `/`
- CloudFront `/api/health`
- `/api/chat` deterministic path
- `/api/chat` Bedrock inference path

---

## Phase 6.5 – Post-deploy Smoke Test（CI 自動化）（已完成）

- Deploy workflow 成功後自動觸發
- 由 GitHub Actions runner 執行 Ansible
- Smoke test 失敗即視為 deploy 失敗（Release Gate）

---

## Phase 7 – Observability（已完成）

本階段導入 **最小可交付（Minimum Viable Observability）**。

### 已實作告警（CloudWatch Alarms）

- ALB 5XX（ELB generated）
- Target Group Unhealthy（HealthyHostCount < 1）
- ECS CPU High（>= 80%, 3 minutes）
- ECS Memory High（>= 80%, 3 minutes）

所有告警皆由 Pulumi 管理，  
並隨 stack 生命週期建立 / 更新 / 銷毀。

---

## Phase 8 – IAM Least Privilege（已完成）

本階段針對專案中所有存取 AWS 的行為進行角色拆分與權限收斂，  
確保 **人類操作、CI/CD、自動化執行期與觀測用途** 各自使用獨立身分，  
並符合 least privilege 與 full lifecycle management 的設計目標。

---

### 設計原則

- 基礎設施、部署流程、執行期與觀測用途使用不同 IAM 身分
- 人類帳號不參與 runtime 或 CI/CD
- CI 不使用長期 access key（改用 OIDC）
- Runtime 僅具備最小必要 API 權限
- 系統在最小權限設計下仍可完成 deploy / update / destroy

---

### IAM 身分與職責分工

#### Infra Admin（Pulumi Operator）

- 實體身分：`ai-qa-chatbot-infra-admin`（IAM User）
- 用途：
  - `pulumi preview`
  - `pulumi up`
  - `pulumi destroy`
- 權限：
  - `AdministratorAccess`（demo / 練習環境）
- 說明：
  - 專責基礎設施生命週期管理
  - 不參與 CI/CD 或應用程式 runtime
  - root 僅用於帳號治理，不作為日常操作身分

---

#### CI/CD Deploy Role（GitHub Actions）

- 身分型態：IAM Role（OIDC Assume Role）
- 用途：
  - 自動化 build / deploy
- 權限範圍（最小可用）：
  - ECR image push（repository scoped）
  - ECS RegisterTaskDefinition
  - ECS UpdateService
  - 限定範圍的 `iam:PassRole`
- 不具備：
  - 基礎設施建立 / 刪除權限
  - Amazon Bedrock API 呼叫權限

---

#### Runtime Role（ECS Task Role）

- 身分型態：IAM Role（ECS Task Role）
- 用途：
  - ECS Fargate 任務執行期間呼叫 Amazon Bedrock
- 僅允許：
  - `bedrock:InvokeModel`
- Resource 限制為：
  - 指定 Nova inference profile ARN
  - 該 profile 可能路由到的同一模型版本 foundation-model ARNs
- 不具備：
  - IAM write 權限
  - ECS / EC2 / SSM 管理能力

---

#### Observer（Read-only Identity）

- 實體身分：`ai-qa-chatbot-observer`（IAM User）
- 權限：
  - AWS managed policy：`ReadOnlyAccess`
- 用途：
  - 系統運行期間的觀測與驗證
- 可執行：
  - 檢視 ECS Service / Task 狀態
  - 檢視 ALB Target Group 健康狀態
  - 檢視 CloudWatch Logs / Metrics / Alarms
  - 透過 CloudFront 公開 API 執行 smoke / functional 驗證
- 不具備：
  - deploy / update / destroy 能力
  - ECR / ECS / IAM write 權限

---

#### Legacy / Bootstrap Identity

- 身分：`ai-qa-chatbot-cli`
- 說明：
  - 專案初期用於快速驗證的高權限帳號
  - 已被 Infra Admin / CI / Runtime / Observer 角色取代
  - 視為 legacy identity，不再用於日常操作

---

### 驗證結果與成果

- Infra Admin 身分已實際用於 Pulumi 操作並完成驗證
- CI / Runtime / Observer 角色皆在最小權限下正常運作
- CI 不再使用長期 access key
- Observer 可觀測但不可修改系統狀態
- 系統仍可完成完整生命週期：
  - deploy / update（CI/CD）
  - destroy（Infra Admin）

---

## Infrastructure Lifecycle（IaC）

- `pulumi preview`：檢視變更影響
- `pulumi up`：建立或更新資源
- `pulumi destroy`：完整銷毀所有資源

---

## Repository Hygiene（已完成 / 進行中）

### 已完成

- 移除臨時 debug 檔案
- 不提交任何憑證或本機設定

### 進行中

- 補齊 `.gitignore`
- 確認 `git clean -xfd` 可安全執行
- 確保 repo 可被第三方 clone 並重現

---

## Roadmap

- [x] Backend on ECS + ALB
- [x] CI/CD automation
- [x] CloudFront + S3 frontend
- [x] Amazon Bedrock integration（Nova）
- [x] Ansible-based smoke test
- [x] Observability（CloudWatch alarms）
- [x] IAM least-privilege hardening
- [ ] Bedrock model configuration refinement
- [ ] Multi-environment（prod stack）
- [ ] README 圖表與架構圖補齊
