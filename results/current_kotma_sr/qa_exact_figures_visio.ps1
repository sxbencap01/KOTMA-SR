param(
    [string]$VisioPath = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603\KOTMA-SR_Fig1-9_Editable_Visio.vsdx"
)

$ErrorActionPreference = "Stop"

$Root = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603"
$MainDir = Join-Path $Root "figures_kbs"
$SuppDir = Join-Path $Root "supplementary_figures"
$QaDir = Join-Path $Root ("visio_exact_qa_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$ZipPath = Join-Path $QaDir "visio_package.zip"
$ExtractDir = Join-Path $QaDir "extracted"

Add-Type -AssemblyName System.Drawing

$Expected = New-Object System.Collections.Generic.List[string]
$Expected.Add((Join-Path $MainDir "Fig1_Graphical_Abstract.png"))
$Expected.Add((Join-Path $MainDir "Fig2_Knowledge_Architecture.png"))
$Expected.Add((Join-Path $MainDir "Fig3_Process_Knowledge.png"))
$Expected.Add((Join-Path $MainDir "Fig4_Structural_Memory.png"))
$Expected.Add((Join-Path $MainDir "Fig5_Sparse_Tail_Gate.png"))
$Expected.Add((Join-Path $MainDir "Fig6_Validation_System.png"))
$Expected.Add((Join-Path $MainDir "Fig7_Primary_Results.png"))
$Expected.Add((Join-Path $MainDir "Fig8_Trust_Calibration.png"))
$Expected.Add((Join-Path $MainDir "Fig9_Evidence_Matrix.png"))
$Expected.Add((Join-Path $SuppDir "FigS1_Grouped_Benchmark.png"))
$Expected.Add((Join-Path $SuppDir "FigS2_Protocol_Sensitivity.png"))
$Expected.Add((Join-Path $SuppDir "FigS3_Sparse_Tail_Cases.png"))
$Expected.Add((Join-Path $SuppDir "FigS4_Gate_Sensitivity.png"))
$Expected.Add((Join-Path $SuppDir "FigS5_Robustness.png"))
$Expected.Add((Join-Path $SuppDir "FigS6_Conditional_Calibration.png"))
$Expected.Add((Join-Path $SuppDir "FigS7_Velocity_Policy.png"))
$Expected.Add((Join-Path $SuppDir "FigS8_Exploratory_GNN.png"))
$Expected.Add((Join-Path $SuppDir "FigS9_Interval_Comparators.png"))

New-Item -ItemType Directory -Path $QaDir | Out-Null
Copy-Item -LiteralPath $VisioPath -Destination $ZipPath
Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractDir

$pageFiles = Get-ChildItem -LiteralPath (Join-Path $ExtractDir "visio\pages") -Filter "page*.xml" | Sort-Object Name
$mediaFiles = Get-ChildItem -LiteralPath (Join-Path $ExtractDir "visio\media") -File | Sort-Object Name
$pagesXmlPath = Join-Path $ExtractDir "visio\pages\pages.xml"
[xml]$pagesXml = Get-Content -LiteralPath $pagesXmlPath
$visioPages = @($pagesXml.Pages.Page)

function Get-ImageInfo([string]$Path) {
    $img = [System.Drawing.Image]::FromFile($Path)
    try {
        return [pscustomobject]@{
            Name = [System.IO.Path]::GetFileName($Path)
            Width = $img.Width
            Height = $img.Height
        }
    } finally {
        $img.Dispose()
    }
}

$expectedImages = @($Expected | ForEach-Object { Get-ImageInfo $_ })
$mediaImages = @($mediaFiles | ForEach-Object { Get-ImageInfo $_.FullName })

$dimensionMatches = 0
foreach ($expected in $expectedImages) {
    foreach ($media in $mediaImages) {
        if ($media.Width -eq $expected.Width -and $media.Height -eq $expected.Height) {
            $dimensionMatches += 1
            break
        }
    }
}

[pscustomobject]@{
    VisioPath = $VisioPath
    PageXmlCount = $pageFiles.Count
    VisioPageIndexCount = $visioPages.Count
    VisioPageNames = @($visioPages | ForEach-Object { $_.NameU })
    EmbeddedMediaCount = $mediaFiles.Count
    ExpectedSourcePngCount = @($expectedImages).Count
    SourceDimensionMatches = $dimensionMatches
    QaDirectory = $QaDir
} | ConvertTo-Json -Depth 3
