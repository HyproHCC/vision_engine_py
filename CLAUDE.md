# VisionEngine —— AI 開發工具入口

**動手前先讀 `ARCHITECTURE.md`**（架構、合約、開發流程全在那裡）。其他文件：README.md（入口與操作）、PROTOCOL.md（TCP 協定）、BUILD.md（打包部署）。

## 最高規則（違反任一條就是錯的）

1. 演算法一律進 `ve_core/`；ve_ui / ve_server 不得含演算法。ve_core 無 I/O / UI / 網路。
2. ve_core 對外輸出一律**原圖座標**；去旋轉座標系不外漏。
3. taught_params JSON 鍵集合**凍結**（tests/test_characterization.py 釘死）；改 schema 走 ARCHITECTURE.md 4.2 的四步驟程序。
4. server 回應行尾固定 `\r\n`（LabVIEW CRLF 模式遇 `\n` 靜默失敗）；協定字串僅 ASCII。
5. 機台/開發機的系統 Python 3.6 **絕對不可動**（其他專案的 LabVIEW Python Node 在用）；一律用專案 venv。
6. 在管線新增參數時，必須同時決定它屬於哪個階段，並更新 ve_ui/session 的失效對照（ARCHITECTURE.md 3.4、6.2）。
7. pytest 全綠才 commit；每次打包 ve_server.exe 就打 git tag。

## 常用指令

```bat
venv\Scripts\python -m pytest tests -q          REM 改程式後必跑
venv\Scripts\python -m pytest tests\test_xxx.py -q   REM 只跑單一測試檔
venv\Scripts\python -m ve_ui.app [影像路徑]      REM 調機工具
venv\Scripts\python -m ve_server.main --mock    REM server（mock 模式）
python test_client.py demo                      REM server 端到端實測（含行尾驗證）
```

## 溝通慣例

回覆與文件一律使用台灣慣用中文（程式、軟體、資料、設定檔；避免大陸用語）。


## 測試資料
- **測試圖片一律用 `testdata/`**；不得再引用專案外資料夾（如 `測試\劃片後檢\backlightTest\0709LowLight\50k`），需要的實圖先收進 testdata/ 再用。
- 實圖:testdata/real/(有角度變化,h/v 兩族線)
- **testdata/ 內是 3840×2748 大圖，沒有明確需要不得用 Read 開圖檔**（一張圖吃掉大量 token）；需要看內容時用腳本讀取數值或縮圖後再看。
