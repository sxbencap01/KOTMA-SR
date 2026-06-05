param(
    [string]$VisioPath = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603\KOTMA-SR_Fig1-9_Editable_Visio.vsdx"
)

$ErrorActionPreference = "Stop"

$Root = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603"
$QaDir = Join-Path $Root ("visio_editable_qa_" + (Get-Date -Format "yyyyMMdd_HHmmss"))
$ZipPath = Join-Path $QaDir "visio_package.zip"
$ExtractDir = Join-Path $QaDir "extracted"

New-Item -ItemType Directory -Path $QaDir | Out-Null
Copy-Item -LiteralPath $VisioPath -Destination $ZipPath
Expand-Archive -LiteralPath $ZipPath -DestinationPath $ExtractDir

[xml]$pagesXml = Get-Content -LiteralPath (Join-Path $ExtractDir "visio\pages\pages.xml")
$pages = @($pagesXml.Pages.Page)
$mediaFiles = @(Get-ChildItem -LiteralPath (Join-Path $ExtractDir "visio\media") -File -ErrorAction SilentlyContinue)

$pageFiles = @(Get-ChildItem -LiteralPath (Join-Path $ExtractDir "visio\pages") -Filter "page*.xml" | Where-Object { $_.Name -match '^page\d+\.xml$' } | Sort-Object {[int](($_.BaseName -replace '^page',''))})
$pageSummaries = New-Object System.Collections.Generic.List[object]
for ($i = 0; $i -lt $pages.Count; $i++) {
    $page = $pages[$i]
    $pageFile = $pageFiles[$i].FullName
    if (-not (Test-Path -LiteralPath $pageFile)) {
        $shapeCount = $null
        $imageShapeCount = $null
    } else {
        [xml]$px = Get-Content -LiteralPath $pageFile
        $shapeNodes = @($px.SelectNodes("//*[local-name()='Shape']"))
        $imageNodes = @($px.SelectNodes("//*[local-name()='ForeignData']"))
        $shapeCount = $shapeNodes.Count
        $imageShapeCount = $imageNodes.Count
    }
    $pageSummaries.Add([pscustomobject]@{
        Name = $page.NameU
        ShapeCount = $shapeCount
        ImageShapeCount = $imageShapeCount
    })
}

[pscustomobject]@{
    VisioPath = $VisioPath
    PageCount = $pages.Count
    EmbeddedMediaCount = $mediaFiles.Count
    EditableFlowPages = @($pageSummaries | Where-Object { $_.Name -match '^Fig[1-6] |^Fig9 ' } | Select-Object Name,ShapeCount,ImageShapeCount)
    SourceImagePages = @($pageSummaries | Where-Object { $_.Name -match 'source image' } | Select-Object Name,ShapeCount,ImageShapeCount)
    QaDirectory = $QaDir
} | ConvertTo-Json -Depth 5
