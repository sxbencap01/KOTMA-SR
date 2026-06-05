param(
    [string]$OutputPath = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603\KOTMA-SR_Fig1-9_Editable_Visio.vsdx"
)

$ErrorActionPreference = "Stop"

$Root = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603"
$MainDir = Join-Path $Root "figures_kbs"
$SuppDir = Join-Path $Root "supplementary_figures"
$Ink = "RGB(38,50,56)"
$Muted = "RGB(82,97,107)"
$Blue = "RGB(220,232,245)"
$BlueStrong = "RGB(36,90,154)"
$BlueLight = "RGB(126,164,210)"
$Red = "RGB(244,217,220)"
$RedStrong = "RGB(176,58,72)"
$RedLight = "RGB(210,132,143)"
$Neutral = "RGB(232,237,242)"
$NeutralStrong = "RGB(142,154,166)"
$White = "RGB(255,255,255)"

Add-Type -AssemblyName System.Drawing

function Set-CellFormula($shape, [string]$cellName, [string]$formula) {
    try { $shape.CellsU($cellName).FormulaU = $formula } catch {}
}

function Setup-Page($page, [string]$name, [double]$w = 16.5, [double]$h = 9.5) {
    $page.Name = $name
    $page.PageSheet.CellsU("PageWidth").FormulaU = "$w in"
    $page.PageSheet.CellsU("PageHeight").FormulaU = "$h in"
}

function Add-Text($page, [double]$x, [double]$y, [double]$w, [double]$h, [string]$text, [string]$color, [string]$size = "12 pt", [string]$bold = "1", [int]$align = 1) {
    $s = $page.DrawRectangle($x, $y, $x + $w, $y + $h)
    $s.Text = $text
    Set-CellFormula $s "FillPattern" "0"
    Set-CellFormula $s "LinePattern" "0"
    Set-CellFormula $s "Char.Color" $color
    Set-CellFormula $s "Char.Size" $size
    Set-CellFormula $s "Char.Style" $bold
    Set-CellFormula $s "Para.HorzAlign" "$align"
    Set-CellFormula $s "VerticalAlign" "1"
    return $s
}

function Add-Box($page, [double]$x1, [double]$y1, [double]$x2, [double]$y2, [string]$text, [string]$fill, [string]$line = $Ink, [string]$size = "10 pt") {
    $s = $page.DrawRectangle($x1, $y1, $x2, $y2)
    $s.Text = $text
    Set-CellFormula $s "FillForegnd" $fill
    Set-CellFormula $s "LineColor" $line
    Set-CellFormula $s "LineWeight" "1.35 pt"
    Set-CellFormula $s "Rounding" "0.12 in"
    Set-CellFormula $s "Char.Color" $Ink
    Set-CellFormula $s "Char.Size" $size
    Set-CellFormula $s "Para.HorzAlign" "1"
    Set-CellFormula $s "VerticalAlign" "1"
    return $s
}

function Add-Line($page, [double]$x1, [double]$y1, [double]$x2, [double]$y2, [string]$color = $Ink, [bool]$arrow = $true, [string]$weight = "1.35 pt") {
    $l = $page.DrawLine($x1, $y1, $x2, $y2)
    Set-CellFormula $l "LineColor" $color
    Set-CellFormula $l "LineWeight" $weight
    if ($arrow) { Set-CellFormula $l "EndArrow" "13" }
    return $l
}

function Add-Circle($page, [double]$cx, [double]$cy, [double]$r, [string]$fill, [string]$line = $fill, [double]$trans = 0) {
    $s = $page.DrawOval($cx - $r, $cy - $r, $cx + $r, $cy + $r)
    Set-CellFormula $s "FillForegnd" $fill
    Set-CellFormula $s "LineColor" $line
    Set-CellFormula $s "FillTransparency" "$trans%"
    Set-CellFormula $s "LineTransparency" "$trans%"
    return $s
}

function Add-Bar($page, [double]$x, [double]$y, [double]$w, [double]$h, [string]$fill, [string]$label = "") {
    $s = $page.DrawRectangle($x, $y, $x + $w, $y + $h)
    Set-CellFormula $s "FillForegnd" $fill
    Set-CellFormula $s "LineColor" $fill
    if ($label) { $s.Text = $label; Set-CellFormula $s "Char.Color" $White; Set-CellFormula $s "Char.Size" "8 pt"; Set-CellFormula $s "Para.HorzAlign" "1"; Set-CellFormula $s "VerticalAlign" "1" }
    return $s
}

function Add-ImagePage($doc, [string]$name, [string]$imagePath) {
    $page = $doc.Pages.Add()
    $image = [System.Drawing.Image]::FromFile($imagePath)
    try {
        $widthPx = [double]$image.Width
        $heightPx = [double]$image.Height
    } finally {
        $image.Dispose()
    }
    $w = 16.5
    $h = [Math]::Round($w * $heightPx / $widthPx, 4)
    Setup-Page $page $name $w $h
    $shape = $page.Import($imagePath)
    Set-CellFormula $shape "PinX" "$($w / 2) in"
    Set-CellFormula $shape "PinY" "$($h / 2) in"
    Set-CellFormula $shape "Width" "$w in"
    Set-CellFormula $shape "Height" "$h in"
    Set-CellFormula $shape "LockAspect" "1"
    return $page
}

function Add-EditableBadge($page, [string]$text = "Editable Visio shapes") {
    Add-Text $page 13.4 0.18 2.7 0.28 $text $Muted "7 pt" "0" 2 | Out-Null
}

function Add-SmallAxis($page, [double]$x0, [double]$y0, [double]$w, [double]$h, [string]$xlabel, [string]$ylabel = "") {
    Add-Line $page $x0 $y0 ($x0 + $w) $y0 $Ink $false "1.2 pt" | Out-Null
    Add-Line $page $x0 $y0 $x0 ($y0 + $h) $Ink $false "1.2 pt" | Out-Null
    Add-Text $page ($x0 + $w * 0.25) ($y0 - 0.55) ($w * 0.5) 0.3 $xlabel $Ink "8.5 pt" "0" | Out-Null
    if ($ylabel) { Add-Text $page ($x0 - 0.8) ($y0 + $h * 0.35) 0.7 0.35 $ylabel $Ink "8 pt" "0" | Out-Null }
}

function Add-ScatterFromCsv($page, [string]$csvPath, [string]$panel, [double]$x0, [double]$y0, [double]$w, [double]$h, [string]$fill, [string]$line, [int]$maxPoints = 220) {
    $rows = @(Import-Csv -LiteralPath $csvPath | Where-Object { $_.panel -eq $panel })
    if ($rows.Count -eq 0) { return }
    if ($rows.Count -gt $maxPoints) {
        $step = [Math]::Ceiling($rows.Count / $maxPoints)
        $sample = New-Object System.Collections.Generic.List[object]
        for ($i = 0; $i -lt $rows.Count; $i += $step) { $sample.Add($rows[$i]) }
        $rows = @($sample.ToArray())
    }
    $xs = @($rows | ForEach-Object { [double]$_.x })
    $ys = @($rows | ForEach-Object { [double]$_.y })
    $xmin = ($xs | Measure-Object -Minimum).Minimum
    $xmax = ($xs | Measure-Object -Maximum).Maximum
    $ymin = ($ys | Measure-Object -Minimum).Minimum
    $ymax = ($ys | Measure-Object -Maximum).Maximum
    foreach ($r in $rows) {
        $px = $x0 + (([double]$r.x - $xmin) / ($xmax - $xmin)) * $w
        $py = $y0 + (([double]$r.y - $ymin) / ($ymax - $ymin)) * $h
        Add-Circle $page $px $py 0.035 $fill $line 18 | Out-Null
    }
}

function Add-HistogramPressure($page, [double]$x0, [double]$y0) {
    Add-Text $page ($x0 - 0.25) ($y0 + 3.7) 3.4 0.35 "a  Pressure remains active" $Ink "13 pt" "1" 0 | Out-Null
    Add-SmallAxis $page $x0 $y0 4.3 3.4 "Executed pressure" "PCB sides"
    $vals = @(
        @{x=0.45; c=1; label="5.0"},
        @{x=0.95; c=1; label="5.4"},
        @{x=1.45; c=5; label="5.6"},
        @{x=1.95; c=13; label="6.0"},
        @{x=2.45; c=12; label="6.4"},
        @{x=2.95; c=2; label="7.0"}
    )
    foreach ($v in $vals) {
        Add-Bar $page ($x0 + $v.x) $y0 0.38 ([double]$v.c / 13.0 * 3.0) $RedStrong | Out-Null
        Add-Text $page ($x0 + $v.x - 0.05) ($y0 - 0.35) 0.5 0.25 $v.label $Ink "7 pt" "0" | Out-Null
    }
    Add-Text $page ($x0 + 1.0) ($y0 + 3.25) 2.1 0.25 "dominant 6.0-6.4" $RedStrong "8 pt" "1" | Out-Null
}

function Add-HistogramVelocity($page, [double]$x0, [double]$y0) {
    Add-Text $page ($x0 - 0.25) ($y0 + 3.7) 3.6 0.35 "b  Velocity is empirically anchored" $Ink "13 pt" "1" 0 | Out-Null
    Add-SmallAxis $page $x0 $y0 4.0 3.4 "Executed velocity" "PCB sides"
    $vals = @(
        @{x=0.75; c=1; label="0.5"},
        @{x=1.65; c=32; label="0.8"},
        @{x=2.75; c=1; label="1.8"}
    )
    foreach ($v in $vals) {
        Add-Bar $page ($x0 + $v.x) $y0 0.62 ([double]$v.c / 32.0 * 3.0) $BlueStrong | Out-Null
        Add-Text $page ($x0 + $v.x + 0.05) ($y0 - 0.35) 0.5 0.25 $v.label $Ink "7 pt" "0" | Out-Null
    }
    Add-Text $page ($x0 + 2.7) ($y0 + 3.0) 1.4 0.25 "32/34 at 0.8" $BlueStrong "8 pt" "1" 0 | Out-Null
}

try {
    $app = [Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
} catch {
    $app = New-Object -ComObject Visio.Application
}
$app.Visible = $true
$app.AlertResponse = 7
$doc = $app.Documents.Add("")

# Fig1 editable overview
$p = $doc.Pages.Item(1)
Setup-Page $p "Fig1 Graphical Abstract"
Add-Text $p 0.7 8.9 15.1 0.45 "KOTMA-SR: knowledge-guided first-article recommendation under sparse histories" $Ink "18 pt" "1" | Out-Null
Add-Text $p 0.45 8.05 3.1 0.35 "Industrial constraint" $BlueStrong "13 pt" "1" | Out-Null
Add-Text $p 6.1 8.05 4.4 0.35 "Process-knowledge-guided reasoning" $RedStrong "13 pt" "1" | Out-Null
Add-Text $p 13.1 8.05 2.4 0.35 "Traceable output" $BlueStrong "13 pt" "1" | Out-Null
Add-Box $p 0.45 6.0 3.0 7.3 "Sparse PCB cases`none executed setting`nper PCB side" $Blue | Out-Null
Add-Box $p 3.25 6.0 5.9 7.3 "New PCB side`ngeometry known;`nSPI hidden" $Neutral | Out-Null
Add-Box $p 6.25 6.45 8.85 7.35 "Case memory`ndescriptor recall" $Blue | Out-Null
Add-Box $p 6.25 5.15 8.85 6.05 "Structural memory`nFGW re-ranking" $Red | Out-Null
Add-Box $p 9.4 5.75 12.35 6.9 "Selection gate`nbounded tail correction`nor CBR default" $Red | Out-Null
Add-Box $p 13.0 5.55 16.0 7.25 "Recommendation card`npressure 6.2`nvelocity 0.8`nverify 6.1-6.3`nevidence + review flag" $Blue | Out-Null
Add-Line $p 5.9 6.85 6.25 6.95 | Out-Null
Add-Line $p 5.9 6.45 6.25 5.55 | Out-Null
Add-Line $p 8.85 6.9 9.4 6.35 | Out-Null
Add-Line $p 8.85 5.6 9.4 6.15 | Out-Null
Add-Line $p 12.35 6.32 13.0 6.32 | Out-Null
Add-Text $p 5.7 4.05 5.2 0.35 "Active pressure search: 5.0-8.0 in 0.1 steps" $RedStrong "11 pt" "1" | Out-Null
Add-Text $p 4.45 3.65 7.5 0.35 "Empirical velocity anchor: default 0.8; engineer override allowed" $BlueStrong "10 pt" "1" | Out-Null
Add-Text $p 3.8 3.2 8.8 0.35 "Retrospective decision support for rapid verification; not autonomous quality optimization" $Muted "9 pt" "0" | Out-Null
$cards = @(
    @{x=0.55;t="Pressure MAE`nCBR 0.324`nKOTMA-SR 0.265`n18.2% lower"},
    @{x=4.55;t="Median error`nCBR 0.4`nKOTMA-SR 0.1`n75.0% lower"},
    @{x=8.55;t="Within +/-0.2`nCBR 41.2`nKOTMA-SR 55.9`n+14.7 pp"},
    @{x=12.55;t="Within +/-0.4`nCBR 73.5`nKOTMA-SR 79.4`n+5.9 pp"}
)
foreach ($c in $cards) { Add-Box $p $c.x 0.35 ($c.x + 3.45) 2.2 $c.t $White "RGB(170,181,192)" "9 pt" | Out-Null }
Add-EditableBadge $p

# Fig2 editable architecture
$p = $doc.Pages.Add(); Setup-Page $p "Fig2 Knowledge Architecture"
Add-Text $p 1.9 8.85 12.7 0.45 "Layered knowledge architecture for leakage-safe first-article reasoning" $Ink "18 pt" "1" | Out-Null
Add-Text $p 0.6 7.85 2.4 0.35 "Knowledge inputs" $BlueStrong "12.5 pt" "1" | Out-Null
Add-Text $p 5.1 7.85 2.5 0.35 "Representations" $BlueStrong "12.5 pt" "1" | Out-Null
Add-Text $p 9.1 7.85 2.7 0.35 "Selective reasoner" $RedStrong "12.5 pt" "1" | Out-Null
Add-Text $p 13.4 7.85 2.6 0.35 "Engineer-facing card" $BlueStrong "12.5 pt" "1" | Out-Null
Add-Box $p 0.45 6.0 3.9 7.3 "PCB geometry`npads, dimensions,`nshape distribution" $Blue | Out-Null
Add-Box $p 0.45 4.1 3.9 5.4 "Process policy`npressure active;`nvelocity anchored" $Blue | Out-Null
Add-Box $p 0.45 2.2 3.9 3.5 "Historical cases`nexecuted pressure;`nSPI hidden at query" $Blue | Out-Null
Add-Box $p 4.85 5.6 8.25 7.15 "Descriptor`nfold-local scaling" $Neutral | Out-Null
Add-Box $p 4.85 3.25 8.25 4.85 "Super-node graph`nphysics-aware PCB" $Neutral | Out-Null
Add-Box $p 9.05 5.8 12.6 7.1 "CBR safeguard`nauditable nearest case" $Blue | Out-Null
Add-Box $p 9.05 4.0 12.6 5.25 "FGW tail correction`nbounded structural update" $Red | Out-Null
Add-Box $p 9.05 2.15 12.6 3.4 "Trust gate`ninterval, OOD, review" $Red | Out-Null
Add-Box $p 13.35 3.35 16.1 5.85 "Recommendation`npressure + velocity`nwindow + evidence" $Blue | Out-Null
Add-Line $p 3.9 6.65 4.85 6.4 | Out-Null
Add-Line $p 3.9 4.75 4.85 4.05 | Out-Null
Add-Line $p 3.9 2.85 4.85 4.05 | Out-Null
Add-Line $p 8.25 6.38 9.05 6.45 | Out-Null
Add-Line $p 8.25 4.05 9.05 4.62 | Out-Null
Add-Line $p 10.82 5.8 10.82 5.25 | Out-Null
Add-Line $p 10.82 4.0 10.82 3.4 | Out-Null
Add-Line $p 12.6 2.78 13.35 4.45 | Out-Null
Add-Text $p 3.7 0.75 9.1 0.35 "All scaling, tuning, calibration and review thresholds remain inside training folds" $RedStrong "11 pt" "1" | Out-Null
Add-Text $p 4.2 0.35 8.5 0.3 "Outer held-out PCB outcomes are revealed only once for retrospective evaluation" $Muted "9 pt" "0" | Out-Null
Add-EditableBadge $p

# Fig3 editable process knowledge
$p = $doc.Pages.Add(); Setup-Page $p "Fig3 Process Knowledge"
Add-HistogramPressure $p 0.75 1.35
Add-HistogramVelocity $p 6.2 1.35
Add-Text $p 11.35 5.1 4.4 0.35 "c  Asymmetric recommendation space" $Ink "13 pt" "1" 0 | Out-Null
Add-Line $p 11.55 3.1 16.0 3.1 $Ink $false "1.2 pt" | Out-Null
Add-Line $p 11.7 5.15 16.0 5.15 $RedStrong $false "2 pt" | Out-Null
for ($i=0; $i -le 30; $i++) { $x = 11.7 + $i * (4.3/30); Add-Line $p $x 5.0 $x 5.3 $RedLight $false "0.5 pt" | Out-Null }
Add-Text $p 12.4 5.75 3.4 0.3 "pressure search: 5.0-8.0, step 0.1" $RedStrong "9 pt" "1" | Out-Null
Add-Line $p 11.7 4.0 16.0 4.0 $BlueLight $false "1.4 pt" | Out-Null
Add-Box $p 13.95 3.85 14.25 4.15 "" $BlueStrong $BlueStrong | Out-Null
Add-Text $p 13.0 3.35 2.6 0.45 "velocity locked to 0.8`n(engineer override allowed)" $BlueStrong "8.5 pt" "1" | Out-Null
Add-Text $p 11.5 2.55 4.4 0.3 "Executable process-setting axis" $Ink "9 pt" "0" | Out-Null
Add-EditableBadge $p

# Fig4 editable structural memory
$p = $doc.Pages.Add(); Setup-Page $p "Fig4 Structural Memory"
$csv4 = Join-Path $MainDir "Fig4_Structural_Memory_SourceData.csv"
Add-Text $p 0.35 8.9 3.0 0.35 "a  Raw pad geometry" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 0.75 1.25 3.2 6.4 "Normalized x" "Normalized y"
Add-ScatterFromCsv $p $csv4 "raw_pads" 0.85 1.45 2.9 5.9 "RGB(142,178,218)" "RGB(142,178,218)" 260
Add-Text $p 4.45 8.9 3.2 0.35 "b  Physics-aware super-nodes" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 4.8 1.25 3.2 6.4 "Normalized x" ""
Add-ScatterFromCsv $p $csv4 "supernodes" 4.9 1.45 2.9 5.9 $RedStrong $RedStrong 140
Add-Text $p 8.35 8.9 3.0 0.35 "c  FGW alignment" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 8.45 1.25 3.2 6.4 "" ""
Add-ScatterFromCsv $p $csv4 "query_nodes" 8.55 1.45 1.25 5.9 $BlueStrong $BlueStrong 80
Add-ScatterFromCsv $p $csv4 "case_nodes" 10.0 1.45 1.25 5.9 $RedStrong $RedStrong 80
Add-Text $p 8.85 8.35 0.8 0.25 "query" $BlueStrong "9 pt" "1" | Out-Null
Add-Text $p 10.75 8.35 0.8 0.25 "case" $RedStrong "9 pt" "1" | Out-Null
for ($i=0; $i -lt 24; $i++) {
    $x1 = 9.2 + (Get-Random -Minimum -0.35 -Maximum 0.35)
    $y1 = 2.0 + (Get-Random -Minimum 0.0 -Maximum 5.3)
    $x2 = 10.55 + (Get-Random -Minimum -0.35 -Maximum 0.35)
    $y2 = 2.0 + (Get-Random -Minimum 0.0 -Maximum 5.3)
    Add-Line $p $x1 $y1 $x2 $y2 $RedLight $false "0.3 pt" | Out-Null
}
Add-Text $p 12.55 8.9 2.9 0.35 "d  Conditional use" $Ink "13 pt" "1" 0 | Out-Null
Add-Box $p 13.0 5.8 16.0 6.85 "Descriptor recall`nstable candidate pool" $Blue | Out-Null
Add-Box $p 13.0 4.1 16.0 5.15 "FGW re-ranking`nstructure-sensitive evidence" $Red | Out-Null
Add-Box $p 13.0 2.4 16.0 3.45 "Bounded correction`nonly for sparse tails" $Red | Out-Null
Add-Line $p 14.5 5.8 14.5 5.15 | Out-Null
Add-Line $p 14.5 4.1 14.5 3.45 | Out-Null
Add-EditableBadge $p

# Fig5 editable sparse-tail gate
$p = $doc.Pages.Add(); Setup-Page $p "Fig5 Sparse Tail Gate"
Add-Text $p 2.6 8.85 11.3 0.45 "Sparse-tail bounded gate: enhance only when historical support is weak" $Ink "18 pt" "1" | Out-Null
Add-Box $p 1.25 6.65 4.3 7.45 "Descriptor CBR`nauditable nearest case" $Blue | Out-Null
Add-Box $p 5.1 6.65 8.3 7.45 "Support audit`nfold-local pressure count" $Neutral | Out-Null
Add-Box $p 9.25 7.25 12.65 7.95 "CBR default`nretain supported case" $Blue | Out-Null
Add-Box $p 9.25 5.75 12.65 6.55 "Bounded correction`nFGW update <= 0.5" $Red | Out-Null
Add-Box $p 13.55 6.65 16.25 7.45 "Executable grid`nround to 0.1 step" $Red | Out-Null
Add-Line $p 4.3 7.05 5.1 7.05 | Out-Null
Add-Line $p 8.3 7.15 9.25 7.6 $BlueStrong | Out-Null
Add-Line $p 8.3 6.95 9.25 6.15 $RedStrong | Out-Null
Add-Text $p 8.35 7.65 1.1 0.3 "supported" $BlueStrong "9 pt" "1" | Out-Null
Add-Text $p 8.35 6.3 1.1 0.3 "sparse tail" $RedStrong "9 pt" "1" | Out-Null
Add-Line $p 12.65 7.6 13.55 7.05 | Out-Null
Add-Line $p 12.65 6.15 13.55 7.05 | Out-Null
Add-Text $p 0.75 4.0 3.4 0.35 "a  Selective action frequency" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 1.15 1.0 5.2 2.65 "" "PCB sides"
Add-Bar $p 1.55 1.0 2.4 2.35 $BlueStrong | Out-Null
Add-Bar $p 4.7 1.0 1.05 0.61 $RedStrong | Out-Null
Add-Text $p 1.6 0.55 2.1 0.25 "CBR default 27" $Ink "8 pt" "0" | Out-Null
Add-Text $p 4.25 0.55 2.2 0.25 "bounded correction 7" $Ink "8 pt" "0" | Out-Null
Add-Text $p 8.65 4.0 4.2 0.35 "b  Board-level gain from bounded gate" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 9.25 1.0 5.7 2.65 "CBR error - KOTMA-SR error" "Held-out PCB sides"
Add-Line $p 11.9 1.0 11.9 3.65 "RGB(170,181,192)" $false "1 pt" | Out-Null
$gains = @(-0.4,0,0,0,0,0,0,0,0,0,0.3,0.4,0.5)
for ($i=0; $i -lt $gains.Count; $i++) {
    $x = 9.25 + (($gains[$i] + 0.45) / 1.0) * 5.7
    $y = 1.15 + ($i / [double]($gains.Count)) * 2.3
    $color = if ($gains[$i] -lt 0) { $BlueStrong } else { $RedStrong }
    Add-Circle $p $x $y 0.055 $color $color 0 | Out-Null
}
Add-EditableBadge $p

# Fig6 editable validation system
$p = $doc.Pages.Add(); Setup-Page $p "Fig6 Validation System"
Add-Text $p 2.5 8.85 11.8 0.45 "Leakage-safe validation system for sparse production histories" $Ink "18 pt" "1" | Out-Null
Add-Box $p 0.75 6.25 4.0 7.65 "34 PCB sides`n21 physical boards" $Blue | Out-Null
Add-Box $p 5.0 6.25 8.25 7.65 "Outer grouped LOBO`nhold out both A/B sides" $Red | Out-Null
Add-Box $p 9.25 6.25 12.5 7.65 "Inner grouped LOBO`ntune only on histories" $Blue | Out-Null
Add-Box $p 13.35 6.25 16.05 7.65 "One reveal`nouter evaluation" $Red | Out-Null
Add-Line $p 4.0 6.95 5.0 6.95 | Out-Null
Add-Line $p 8.25 6.95 9.25 6.95 | Out-Null
Add-Line $p 12.5 6.95 13.35 6.95 | Out-Null
Add-Text $p 3.75 5.35 9.4 0.35 "Outer outcomes never enter scaling, tuning, calibration or recommendation" $RedStrong "11 pt" "1" | Out-Null
$bottom = @(
    @{x=0.9; f=$Blue; t="Baselines`nCBR, median,`nunconstrained OT"},
    @{x=4.2; f=$Red; t="Ablations`nFGW, safeguard,`nbounded update"},
    @{x=7.5; f=$Blue; t="Small-sample`n5, 10, 20,`nall histories"},
    @{x=10.8; f=$Red; t="Controls`nrandom memory,`npad-count only"},
    @{x=14.1; f=$Blue; t="Trust`nintervals, OOD,`nreview, latency"}
)
foreach ($b in $bottom) { Add-Box $p $b.x 2.0 ($b.x + 2.45) 3.55 $b.t $b.f | Out-Null }
Add-Text $p 4.0 0.65 8.8 0.35 "Evidence matrix: performance + mechanism + robustness + transparency" $Ink "11 pt" "1" | Out-Null
Add-EditableBadge $p

# Fig7 and Fig8 retain exact quantitative source figure as images.
Add-ImagePage $doc "Fig7 Primary Results - source image" (Join-Path $MainDir "Fig7_Primary_Results.png") | Out-Null
Add-ImagePage $doc "Fig8 Trust Calibration - source image" (Join-Path $MainDir "Fig8_Trust_Calibration.png") | Out-Null

# Fig9 editable evidence summary
$p = $doc.Pages.Add(); Setup-Page $p "Fig9 Evidence Matrix"
Add-Text $p 0.55 8.9 4.0 0.35 "a  Clean ablation" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 0.85 4.9 3.2 3.1 "MAE" ""
Add-Bar $p 0.85 7.2 1.5 0.45 $RedStrong | Out-Null
Add-Bar $p 0.85 6.35 1.85 0.45 $BlueLight | Out-Null
Add-Bar $p 0.85 5.5 1.9 0.45 $BlueLight | Out-Null
Add-Bar $p 0.85 4.65 2.1 0.45 $BlueLight | Out-Null
Add-Text $p 2.95 7.18 1.8 0.25 "Sparse-tail correction" $Ink "8 pt" "0" 0 | Out-Null
Add-Text $p 2.95 6.33 1.5 0.25 "Descriptor CBR" $Ink "8 pt" "0" 0 | Out-Null
Add-Text $p 2.95 5.48 1.6 0.25 "Descriptor + FGW" $Ink "8 pt" "0" 0 | Out-Null
Add-Text $p 2.95 4.63 1.2 0.25 "FGW only" $Ink "8 pt" "0" 0 | Out-Null
Add-Text $p 5.0 8.9 3.3 0.35 "b  Geometry perturbation" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 5.35 4.9 2.0 3.1 "Geometry perturbation (%)" "Recommendation shift"
Add-Line $p 5.35 6.45 7.25 6.45 $RedStrong $false "1.2 pt" | Out-Null
foreach ($x in @(5.35,6.3,7.25)) { Add-Circle $p $x 6.45 0.06 $RedStrong $RedStrong | Out-Null }
Add-Text $p 8.05 8.9 3.5 0.35 "c  Small-sample degradation" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 8.45 4.9 2.0 3.1 "Historical PCB sides" "MAE"
Add-Line $p 8.55 7.1 9.15 7.65 $BlueStrong $false "1.2 pt" | Out-Null
Add-Line $p 9.15 7.65 9.7 6.25 $BlueStrong $false "1.2 pt" | Out-Null
Add-Line $p 9.7 6.25 10.25 6.05 $BlueStrong $false "1.2 pt" | Out-Null
foreach ($pt in @(@(8.55,7.1),@(9.15,7.65),@(9.7,6.25),@(10.25,6.05))) { Add-Circle $p $pt[0] $pt[1] 0.07 $BlueStrong $BlueStrong | Out-Null }
Add-Line $p 8.55 6.8 9.15 6.35 $RedStrong $false "1.2 pt" | Out-Null
Add-Line $p 9.15 6.35 9.7 5.55 $RedStrong $false "1.2 pt" | Out-Null
Add-Line $p 9.7 5.55 10.25 5.0 $RedStrong $false "1.2 pt" | Out-Null
foreach ($pt in @(@(8.55,6.8),@(9.15,6.35),@(9.7,5.55),@(10.25,5.0))) { Add-Circle $p $pt[0] $pt[1] 0.07 $RedStrong $RedStrong | Out-Null }
Add-Text $p 11.6 8.9 3.2 0.35 "d  Negative controls" $Ink "13 pt" "1" 0 | Out-Null
Add-SmallAxis $p 12.05 4.9 3.3 3.1 "MAE" ""
Add-Bar $p 12.05 7.15 1.45 0.48 $RedStrong | Out-Null
Add-Bar $p 12.05 6.25 1.85 0.48 $BlueLight | Out-Null
Add-Bar $p 12.05 5.35 2.1 0.48 $BlueLight | Out-Null
Add-Text $p 14.3 7.17 1.0 0.25 "KOTMA-SR" $Ink "8 pt" "0" 0 | Out-Null
Add-Text $p 14.3 6.27 1.8 0.25 "Nearest pad-count only" $Ink "8 pt" "0" 0 | Out-Null
Add-Text $p 14.3 5.37 1.4 0.25 "Training median" $Ink "8 pt" "0" 0 | Out-Null
Add-Box $p 4.1 1.1 12.6 2.05 "Evidence boundary`nAblation, perturbation, small-sample and negative-control checks support bounded retrospective claims; external deployment remains future work." $Neutral | Out-Null
Add-EditableBadge $p

# Supplementary figures remain exact source images.
$supps = @(
    @{ Page = "FigS1 Grouped Benchmark - source image"; File = Join-Path $SuppDir "FigS1_Grouped_Benchmark.png" },
    @{ Page = "FigS2 Protocol Sensitivity - source image"; File = Join-Path $SuppDir "FigS2_Protocol_Sensitivity.png" },
    @{ Page = "FigS3 Sparse Tail Cases - source image"; File = Join-Path $SuppDir "FigS3_Sparse_Tail_Cases.png" },
    @{ Page = "FigS4 Gate Sensitivity - source image"; File = Join-Path $SuppDir "FigS4_Gate_Sensitivity.png" },
    @{ Page = "FigS5 Robustness - source image"; File = Join-Path $SuppDir "FigS5_Robustness.png" },
    @{ Page = "FigS6 Conditional Calibration - source image"; File = Join-Path $SuppDir "FigS6_Conditional_Calibration.png" },
    @{ Page = "FigS7 Velocity Policy - source image"; File = Join-Path $SuppDir "FigS7_Velocity_Policy.png" },
    @{ Page = "FigS8 Exploratory GNN - source image"; File = Join-Path $SuppDir "FigS8_Exploratory_GNN.png" },
    @{ Page = "FigS9 Interval Comparators - source image"; File = Join-Path $SuppDir "FigS9_Interval_Comparators.png" }
)
foreach ($s in $supps) {
    Add-ImagePage $doc $s.Page $s.File | Out-Null
}

$resolved = [System.IO.Path]::GetFullPath($OutputPath)
$dir = [System.IO.Path]::GetDirectoryName($resolved)
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
if (Test-Path -LiteralPath $resolved) {
    $timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
    $backup = [System.IO.Path]::Combine($dir, "KOTMA-SR_Fig1-9_Editable_Visio.backup_before_editable_$timestamp.vsdx")
    Copy-Item -LiteralPath $resolved -Destination $backup
    Write-Output "Backed up existing Visio document: $backup"
}
$doc.SaveAs($resolved)
$app.ActiveWindow.Page = $doc.Pages.Item(1)
Write-Output "Saved editable hybrid Visio document: $resolved"
Write-Output "Pages: $($doc.Pages.Count)"
foreach ($page in @($doc.Pages)) { Write-Output ("Page: {0}" -f $page.Name) }
