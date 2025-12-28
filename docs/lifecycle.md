# 系統生命週期與使用說明（System Lifecycle and Usage Guide）

本文件說明如何使用本專案所提供的材料（Pulumi、Ansible、CI/CD Pipeline），  
在 AWS 上完成基礎設施建置、應用程式部署、系統驗證，  
並支援完整的系統生命週期（deploy / update / destroy）。

---

## 1. Repository 結構概覽

本 repository 主要由以下幾個部分組成：

- 基礎設施即程式碼（Infrastructure as Code, Pulumi）
- 應用程式原始碼（後端與前端）
- CI/CD Pipeline（GitHub Actions）
- 持續部署與驗證機制（Ansible）

本文件重點在於說明：  
**這些材料如何被組合使用，而非個別工具的教學。**

---

## 2. 基礎設施生命週期（Infrastructure Lifecycle – Pulumi）

### 2.1 Stack 模型

- 每一個 Pulumi stack 代表一個獨立環境（例如 dev、prod）。
- 所有 AWS 基礎設施皆由 Pulumi 管理與定義。
- 環境之間使用相同的 IaC 程式碼，僅以 stack 區分。

---

### 2.2 建立與更新（Provision / Update）

基礎設施的建立與更新由 Pulumi 負責執行。  
在套用任何變更前，會先檢視預期的資源異動內容。

```bash
cd infra
pulumi stack select dev
pulumi preview
```
確認變更內容後，實際套用基礎設施設定：

```bash 
pulumi up
```

Pulumi 會建立或更新所有定義於 IaC 中的 AWS 資源，
包含 VPC、ALB、ECS、S3、CloudFront 及相關 IAM 角色。

基礎設施完成後，可透過 stack outputs
取得後續部署與驗證所需的動態資訊：

```bash 
pulumi stack output cloudfront_domain_name
pulumi stack output ecs_cluster_name
pulumi stack output ecs_service_name
```

### 2.3 銷毀與重建（Destroy / Recreate）

為驗證 Infrastructure as Code 的可重現性，
可完整銷毀指定 stack 所建立的所有 AWS 資源：

```bash 
pulumi destroy
```

所有資源皆可由相同的 Pulumi 程式碼再次重建，
基礎設施本身不依賴手動建立，可由相同 IaC 程式碼重建（CI/CD IAM 屬於一次性平台設定，見 README Phase 8）。

此流程用於驗證系統是否支援完整生命週期管理
（deploy / update / destroy / recreate）。


---

## 3. 應用程式部署流程（Application Deployment Flow）

### 3.1 CI 觸發方式

- CI/CD pipeline 目前採用 **手動觸發（workflow_dispatch）**。
- 部署行為由操作人員在 GitHub Actions 介面中主動啟動。
- 此設計可避免每次程式碼變更即影響執行中環境。

此設計用於示範環境控制與部署審慎性，
避免在示範或評估情境下因頻繁變更影響穩定服務。


---

### 3.2 Build 階段（CI）

- 建置後端應用程式的 container image。
- 依照版本策略標記 image（例如 commit SHA）。
- 將 image 推送至 Amazon ECR。
- 實際建置與推送行為由 GitHub Actions workflow 執行（手動觸發）。

---

### 3.3 部署階段的責任分離

- **CI（GitHub Actions）**
  - 負責 image 建置與推送
  - 負責部署流程觸發

- **CD（Ansible）**
  - 負責更新 ECS task definition
  - 負責更新 ECS service
  - 負責部署後狀態驗證

CI pipeline 不負責基礎設施變更，  
基礎設施生命週期仍完全由 Pulumi 管理。

---
### 3.3.1 Frontend 部署與必要 IAM 權限

本專案的 deploy workflow 同時包含：

- Backend：ECR image → Ansible 更新 ECS service
- Frontend：將 `frontend/` 靜態檔案同步至 frontend S3 bucket

因此 CI/CD Deploy Role（GitHub Actions assume role）需具備
**限定單一 frontend bucket 範圍**的 S3 權限，以支援：

- `aws s3 sync --delete`（需要 `s3:ListBucket` / `s3:PutObject` / `s3:DeleteObject`）

CI/CD IAM policy（例如 `ai-qa-chatbot-ci-frontend-s3-dev`）由 Infra Admin 一次性建立並掛載，
不隨 Pulumi stack destroy / recreate。

---

### 3.4 部署完成條件

一次成功的應用程式部署需滿足以下條件：

- 新版 image 已成功推送至 Amazon ECR。
- ECS service 已更新並進入穩定狀態。
- 後續 smoke test 驗證通過。

---

## 4. 使用 Ansible 進行持續部署（Continuous Deployment）

### 4.1 Ansible 的角色定位

- Ansible 作為實際的 CD（Continuous Deployment）執行引擎。
- 透過 AWS API 操作 ECS，而非透過 SSH 連線。

### 4.2 部署流程概念

- 取得現有 ECS task definition。
- 註冊新版本 task definition。
- 更新 ECS service 使用新版本。
- 等待服務進入穩定狀態。

---

## 5. 部署後驗證（Post-deploy Smoke Test）

部署完成後，系統會執行基本的 smoke test，  
以確認對外服務與核心功能可正常運作。

---

### 5.1 驗證目的

- 作為應用程式部署的 release gate。
- 確保新版本服務可正常對外提供。
- 在正式使用前即時發現重大問題。

---

### 5.2 驗證方式

驗證行為以「黑箱測試（black-box test）」為原則，  
僅透過實際對外入口進行請求，不依賴內部狀態。

主要驗證項目包含：

- 前端服務是否可正常存取
- 後端 API 是否回應正常
- AI 問答功能是否可成功呼叫

---

### 5.3 驗證項目與範例
> 將 `<cloudfront-domain>` 替換為實際 CloudFront Domain，例如：`dxxxx.cloudfront.net`


**前端服務入口**

**Linux / macOS（bash）**

```bash
curl https://<cloudfront-domain>/
```

**Windows（PowerShell）**

```powershell
curl.exe "https://<cloudfront-domain>/"
```

**後端健康檢查 API**

**Linux / macOS（bash）**
```bash
curl "https://<cloudfront-domain>/api/health"
```

**Windows（PowerShell）**

```powershell
curl.exe "https://<cloudfront-domain>/api/health"
```

**Chat API（deterministic path）**

**Linux / macOS（bash）**


```bash
curl -X POST https://<cloudfront-domain>/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"What time is it?"}'
```
**Windows（PowerShell）**

```powershell
curl.exe -X POST "https://<cloudfront-domain>/api/chat" `
  -H "Content-Type: application/json" `
  -d "{`"question`":`"What time is it?`"}"
```

**Chat API（AI inference path）**

**Linux / macOS（bash）**
```bash
curl -X POST https://<cloudfront-domain>/api/chat \
  -H "Content-Type: application/json" \
  -d '{"question":"Hello"}'
```
**Windows（PowerShell）**
```powershell
curl.exe -X POST "https://<cloudfront-domain>/api/chat" `
  -H "Content-Type: application/json" `
  -d "{`"question`":`"Hello`"}"
```


### 5.4 驗證結果判定

- 任一驗證項目失敗，即視為部署失敗。
- Smoke test 未通過時，不應進行後續釋出或切換流量。
- 驗證成功，代表本次部署可安全對外提供服務。

---

## 6. 系統執行期請求流程（Runtime Request Flow）

- 使用者透過 CloudFront 存取系統。
- 靜態內容由私有 S3 Bucket 提供。
- API 請求由 CloudFront 導向 ALB。
- ALB 將請求轉送至 ECS Fargate。
- 後端服務依需求呼叫 Amazon Bedrock 進行 AI 推論。

---

## 7. 可觀測性（Observability）

- 應用程式日誌集中至 CloudWatch Logs。
- 基礎監控涵蓋：
  - 負載平衡錯誤率
  - 服務健康狀態
  - ECS 資源使用率
- 關鍵指標設有告警機制。

---

## 8. IAM 與安全模型（IAM and Security Model）

- 依角色拆分權限：
  - 基礎設施管理
  - CI/CD 部署
  - 執行期服務
  - 觀測用途
- 各角色皆遵循 least privilege 原則。
- CI 與 Runtime 權限明確分離。

---

## 9. 系統生命週期總結

本專案實際驗證以下能力：

- 可部署（Deploy）
- 可更新（Update）
- 可完整銷毀（Destroy）
- 可由程式碼重新建立（Recreate）

系統可在乾淨的 AWS 帳號中，  
僅依賴本 repository 所提供的材料完成重建。
