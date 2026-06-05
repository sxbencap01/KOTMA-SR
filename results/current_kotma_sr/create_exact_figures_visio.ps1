param(
    [string]$OutputPath = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603\KOTMA-SR_Fig1-9_Editable_Visio.vsdx"
)

$ErrorActionPreference = "Stop"

$Root = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603"
$MainDir = Join-Path $Root "figures_kbs"
$SuppDir = Join-Path $Root "supplementary_figures"

$Figures = @(
    @{ Page = "Fig1 Graphical Abstract"; File = Join-Path $MainDir "Fig1_Graphical_Abstract.png" },
    @{ Page = "Fig2 Knowledge Architecture"; File = Join-Path $MainDir "Fig2_Knowledge_Architecture.png" },
    @{ Page = "Fig3 Process Knowledge"; File = Join-Path $MainDir "Fig3_Process_Knowledge.png" },
    @{ Page = "Fig4 Structural Memory"; File = Join-Path $MainDir "Fig4_Structural_Memory.png" },
    @{ Page = "Fig5 Sparse Tail Gate"; File = Join-Path $MainDir "Fig5_Sparse_Tail_Gate.png" },
    @{ Page = "Fig6 Validation System"; File = Join-Path $MainDir "Fig6_Validation_System.png" },
    @{ Page = "Fig7 Primary Results"; File = Join-Path $MainDir "Fig7_Primary_Results.png" },
    @{ Page = "Fig8 Trust Calibration"; File = Join-Path $MainDir "Fig8_Trust_Calibration.png" },
    @{ Page = "Fig9 Evidence Matrix"; File = Join-Path $MainDir "Fig9_Evidence_Matrix.png" },
    @{ Page = "FigS1 Grouped Benchmark"; File = Join-Path $SuppDir "FigS1_Grouped_Benchmark.png" },
    @{ Page = "FigS2 Protocol Sensitivity"; File = Join-Path $SuppDir "FigS2_Protocol_Sensitivity.png" },
    @{ Page = "FigS3 Sparse Tail Cases"; File = Join-Path $SuppDir "FigS3_Sparse_Tail_Cases.png" },
    @{ Page = "FigS4 Gate Sensitivity"; File = Join-Path $SuppDir "FigS4_Gate_Sensitivity.png" },
    @{ Page = "FigS5 Robustness"; File = Join-Path $SuppDir "FigS5_Robustness.png" },
    @{ Page = "FigS6 Conditional Calibration"; File = Join-Path $SuppDir "FigS6_Conditional_Calibration.png" },
    @{ Page = "FigS7 Velocity Policy"; File = Join-Path $SuppDir "FigS7_Velocity_Policy.png" },
    @{ Page = "FigS8 Exploratory GNN"; File = Join-Path $SuppDir "FigS8_Exploratory_GNN.png" },
    @{ Page = "FigS9 Interval Comparators"; File = Join-Path $SuppDir "FigS9_Interval_Comparators.png" }
)

Add-Type -AssemblyName System.Drawing

function Set-CellFormula($shape, [string]$cellName, [string]$formula) {
    try { $shape.CellsU($cellName).FormulaU = $formula } catch {}
}

function Setup-PageForImage($page, [string]$name, [string]$imagePath) {
    $image = [System.Drawing.Image]::FromFile($imagePath)
    try {
        $widthPx = [double]$image.Width
        $heightPx = [double]$image.Height
    } finally {
        $image.Dispose()
    }

    $pageWidth = 16.5
    $pageHeight = [Math]::Round($pageWidth * $heightPx / $widthPx, 4)
    $page.Name = $name
    $page.PageSheet.CellsU("PageWidth").FormulaU = "$pageWidth in"
    $page.PageSheet.CellsU("PageHeight").FormulaU = "$pageHeight in"
    return @{ Width = $pageWidth; Height = $pageHeight }
}

function Add-FigureImage($page, [string]$imagePath, [double]$pageWidth, [double]$pageHeight) {
    # Use the source PNG as the canonical visual layer so Visio stays identical
    # to the manuscript figure exports in figures_kbs/supplementary_figures.
    $shape = $page.Import($imagePath)
    Set-CellFormula $shape "PinX" "$($pageWidth / 2) in"
    Set-CellFormula $shape "PinY" "$($pageHeight / 2) in"
    Set-CellFormula $shape "Width" "$pageWidth in"
    Set-CellFormula $shape "Height" "$pageHeight in"
    Set-CellFormula $shape "LockAspect" "1"
    Set-CellFormula $shape "LockMoveX" "1"
    Set-CellFormula $shape "LockMoveY" "1"
    return $shape
}

foreach ($figure in $Figures) {
    if (-not (Test-Path -LiteralPath $figure.File)) {
        throw "Missing figure source: $($figure.File)"
    }
}

try {
    $app = [Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
} catch {
    $app = New-Object -ComObject Visio.Application
}
$app.Visible = $true
$app.AlertResponse = 7

$doc = $app.Documents.Add("")

for ($i = 0; $i -lt $Figures.Count; $i++) {
    if ($i -eq 0) {
        $page = $doc.Pages.Item(1)
    } else {
        $page = $doc.Pages.Add()
    }
    $pageInfo = Setup-PageForImage $page $Figures[$i].Page $Figures[$i].File
    Add-FigureImage $page $Figures[$i].File $pageInfo.Width $pageInfo.Height | Out-Null
}

$resolved = [System.IO.Path]::GetFullPath($OutputPath)
$dir = [System.IO.Path]::GetDirectoryName($resolved)
if (-not (Test-Path -LiteralPath $dir)) {
    New-Item -ItemType Directory -Path $dir | Out-Null
}

if (Test-Path -LiteralPath $resolved) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backup = [System.IO.Path]::Combine($dir, "KOTMA-SR_Fig1-9_Editable_Visio.backup_$timestamp.vsdx")
    Copy-Item -LiteralPath $resolved -Destination $backup
    Write-Output "Backed up existing Visio document: $backup"
}

$doc.SaveAs($resolved)
$app.ActiveWindow.Page = $doc.Pages.Item(1)
Write-Output "Saved Visio document: $resolved"
Write-Output "Pages: $($doc.Pages.Count)"
foreach ($page in @($doc.Pages)) {
    Write-Output ("Page: {0}" -f $page.Name)
}
