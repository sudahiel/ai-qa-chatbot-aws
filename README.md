# AI Q&A Chatbot on AWS (Work In Progress)

本專案為一個工程導向（Engineering-focused）練習專案，目標是透過 Infrastructure as Code（Pulumi）與雲端原生服務，逐步建構一個可部署、可維運的 AI 問答後端系統。

本 README 為「活文件（Living Document）」：用來記錄目前已完成的狀態、設計決策與下一步規劃，而非最終使用說明文件。

---

## 專案目標

- 使用 Pulumi 管理 AWS 基礎設施（IaC）
- 建立可對外服務的後端 API（FastAPI）
- 逐步導入 CI/CD、權限收斂（Least Privilege）
- 練習雲端系統的工程化建置流程

---

## 目前進度（Current Status）

### 環境資訊
- Pulumi Stack：`dev`
- AWS Region：`ap-northeast-1`（Tokyo）
- Backend Runtime：ECS Fargate
- Load Balancer：Application Load Balancer（ALB）

### 已確認資源（Pulumi stack outputs）
- S3 Bucket：`ai-qa-chatbot-infra-dev-assets`
- ECR Repository：`ai-qa-chatbot-infra-dev`
- ECS Cluster：`appCluster-05803ac`
- ECS Service：`backendService-c071a06`

---

## Phase 2 – Backend on AWS（已完成）

### 架構摘要
- 使用 Pulumi 建立 ECS Fargate + ALB
- FastAPI（uvicorn）作為後端 API
- ALB 透過 Target Group 將流量導向 ECS task
- Target Group 採用 IP mode

### 對外存取（ALB DNS）
- `appAlb-d31e92c-1793100177.ap-northeast-1.elb.amazonaws.com`

（提示：瀏覽器/ curl 請自行加上 `http://`）

### 健康檢查
- Endpoint：`GET /health`
- Expected：HTTP 200
- 狀態：Target Group = `Healthy`（已驗證）

### 其他可用路徑
- Swagger UI：`GET /docs`
- OpenAPI Spec：`GET /openapi.json`

### 備註
- 根路徑 `GET /` 回傳 404 為預期行為（未實作 root route）
- `server: uvicorn` header 代表請求已到達後端服務

---

## Phase 3 – CI/CD Automation on ECS（已完成）

### 已完成自動化部署流程
- 使用 GitHub Actions 建立 CI/CD pipeline
- Push code 至 `master` 後自動執行：
  1. Docker build backend image
  2. Tag image（`gitsha-<commit>` / `dev-latest`）
  3. Push image 至 Amazon ECR
  4. 產生新的 ECS task definition（更新 image）
  5. 更新 ECS service，進行 rolling update

### 驗證方式
- ECR 中可看到對應 commit 的 image tag
- ECS running task image 與最新 commit 對齊
- ALB `/health` endpoint 在部署後仍回傳 HTTP 200

### 後續優化方向（仍在進行）
- IAM 權限由寬轉為 least privilege（將於 README 補充收斂紀錄）
- 加入更明確的 deployment guard（例如環境區分）

---

## 待完成事項（Todo）

- [x] 建立 GitHub Actions CI/CD workflow
- [x] 自動 build / tag / push Docker image 到 ECR
- [x] 自動更新 ECS task definition 並進行 rolling update
- [ ] IAM 權限由寬轉為 least privilege（並在 README 記錄收斂步驟）
- [ ] 後端功能逐步完善（AI 邏輯）


---

## 專案備註

- 本專案仍在持續演進中
- README 內容會隨實作進度調整
