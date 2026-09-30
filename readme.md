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

## 打包（Windows）

首次打包时，在项目目录安装构建依赖（没有 `.venv` 时先按上文创建）：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
.\pack.bat
```

以后直接运行 `pack.bat` 即可。脚本固定使用项目的 `.venv`，从其他工作目录调用也可以，不需要安装 7-Zip。

输出为单文件 `dist\Subtitle Mask-1.3.0.exe`。直接运行或复制这一个 EXE 即可，无需另外安装 Python，也不需要附带依赖目录。

程序运行时会自动把内置依赖解压到系统临时目录，关闭后自动清理。窗口位置、颜色和快捷键仍按原有逻辑保存到运行目录的 `window_data.json`，这个配置文件不需要随 EXE 分发。

构建成功后才替换发布 EXE；构建失败时脚本返回非零退出码，已有的发布 EXE 保持不变。版本号在 `pack.bat` 的 `versionNumber` 中修改。
