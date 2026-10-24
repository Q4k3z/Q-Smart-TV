$ErrorActionPreference = 'Stop'
$projectRoot = Split-Path -Parent $PSScriptRoot
$compilerPath = Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
if (-not (Test-Path -LiteralPath $compilerPath)) {
    $compilerPath = Join-Path $env:WINDIR 'Microsoft.NET\Framework\v4.0.30319\csc.exe'
}
if (-not (Test-Path -LiteralPath $compilerPath)) { throw 'Không tìm thấy trình biên dịch .NET Framework của Windows.' }

# Draw the existing Q mark locally; no downloaded icon or build dependencies.
Add-Type -AssemblyName System.Drawing
$assetDirectory = Join-Path $PSScriptRoot 'assets'
New-Item -ItemType Directory -Path $assetDirectory -Force | Out-Null
$iconPath = Join-Path $assetDirectory 'qsmarttv.ico'
$bitmap = [System.Drawing.Bitmap]::new(64, 64)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
$brush = [System.Drawing.Drawing2D.LinearGradientBrush]::new(
    [System.Drawing.Rectangle]::new(0, 0, 64, 64),
    [System.Drawing.Color]::FromArgb(139, 92, 246),
    [System.Drawing.Color]::FromArgb(244, 114, 100), 45)
$font = [System.Drawing.Font]::new('Segoe UI', 35, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
$format = [System.Drawing.StringFormat]::new()
$format.Alignment = [System.Drawing.StringAlignment]::Center
$format.LineAlignment = [System.Drawing.StringAlignment]::Center
$icon = $null
$stream = $null
try {
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.FillRectangle($brush, 0, 0, 64, 64)
    $graphics.DrawString('Q', $font, [System.Drawing.Brushes]::White, [System.Drawing.RectangleF]::new(0, -2, 64, 64), $format)
    $icon = [System.Drawing.Icon]::FromHandle($bitmap.GetHicon())
    $stream = [System.IO.File]::Create($iconPath)
    $icon.Save($stream)
}
finally {
    if ($stream) { $stream.Dispose() }
    if ($icon) { $icon.Dispose() }
    $format.Dispose(); $font.Dispose(); $brush.Dispose(); $graphics.Dispose(); $bitmap.Dispose()
}

$outputPath = Join-Path $projectRoot 'Q Smart TV.exe'
& $compilerPath /nologo /target:winexe /optimize+ /platform:anycpu /reference:System.Windows.Forms.dll "/win32icon:$iconPath" "/out:$outputPath" (Join-Path $PSScriptRoot 'QuickStart.cs')
if ($LASTEXITCODE -ne 0) { throw 'Tạo EXE thất bại.' }
Write-Output "Đã tạo: $outputPath"
