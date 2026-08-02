param(
    [string]$PptxPath = "D:\smt\predictionprocess202603\KOTMA-SR_publish\results\current_kotma_sr\Fig1_KOTMA_SR_Graphical_Abstract_Editable.pptx",
    [string]$PngPath = "D:\smt\predictionprocess202603\KOTMA-SR_publish\results\current_kotma_sr\Fig1_KOTMA_SR_Graphical_Abstract_Editable.png"
)

$ErrorActionPreference = "Stop"
$ppt = $null
$pres = $null
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $ppt.Visible = -1
    $pres = $ppt.Presentations.Open($PptxPath, $true, $false, $false)
    $pres.Slides.Item(1).Export($PngPath, "PNG", 2400, 1600)
    Write-Output "Saved preview PNG: $PngPath"
}
finally {
    if ($pres -ne $null) { $pres.Close() }
    if ($ppt -ne $null) {
        $ppt.Quit()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
    }
}
