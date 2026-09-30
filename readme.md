# Subtitle Mask
简单的字幕遮挡小工具，半透明遮挡，支持一键开关。

鼠标移到横条上时显示 7 个颜色圆点，点击即可切换横条颜色，所选颜色会自动保存。勾选 `Blur mask` 后，移开鼠标会隐藏按钮并显示无色的透明模糊效果；不勾选时则保留所选纯色遮挡。

[点此下载](https://github.com/chocovon/subtitle-mask/releases/download/v1.3.0/Subtitle.Mask-1.3.0.zip)

<img src="./image/demo.gif" alt="Subtitle Mask demo"/>

## 从源码运行（Windows）

在项目目录中执行（已验证 Python 3.12）：

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

如果已有 `.venv`，跳过第一条命令。使用 PyCharm 时，项目解释器应选择本项目的 `.venv\Scripts\python.exe`。

代码中的 `import win32gui` 由 `pywin32` 包提供，请勿直接执行 `pip install win32gui`。窗口模糊功能还需要 `BlurWindow`，以上依赖文件已包含两者。
