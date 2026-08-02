param(
    [string]$OutputPath = "D:\smt\predictionprocess202603\KOTMA-SR_publish\results\current_kotma_sr\Fig1_KOTMA_SR_Graphical_Abstract_Editable.pptx"
)

$ErrorActionPreference = "Stop"

$msoTrue = -1
$msoFalse = 0
$ppLayoutBlank = 12
$ppSaveAsOpenXMLPresentation = 24

function Add-Shape {
    param(
        $Slide,
        [int]$Type,
        [double]$X,
        [double]$Y,
        [double]$W,
        [double]$H,
        [string]$Text = "",
        [int]$Fill = 0xFFFFFF,
        [int]$Line = 0x1F4E8C,
        [double]$LineWeight = 1.0,
        [string]$Font = "Arial",
        [double]$Size = 11,
        [int]$FontColor = 0x111111,
        [bool]$Bold = $false,
        [int]$Align = 1
    )
    $shape = $Slide.Shapes.AddShape($Type, $X, $Y, $W, $H)
    $shape.Fill.ForeColor.RGB = $Fill
    $shape.Line.ForeColor.RGB = $Line
    $shape.Line.Weight = $LineWeight
    if ($Text.Length -gt 0) {
        $shape.TextFrame2.TextRange.Text = $Text
        $shape.TextFrame2.MarginLeft = 8
        $shape.TextFrame2.MarginRight = 8
        $shape.TextFrame2.MarginTop = 5
        $shape.TextFrame2.MarginBottom = 5
        $shape.TextFrame2.VerticalAnchor = 3
        $shape.TextFrame2.TextRange.Font.Name = $Font
        $shape.TextFrame2.TextRange.Font.Size = $Size
        $shape.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $FontColor
        if ($Bold) { $shape.TextFrame2.TextRange.Font.Bold = $msoTrue }
        $shape.TextFrame2.TextRange.ParagraphFormat.Alignment = $Align
    }
    return $shape
}

function Add-Text {
    param(
        $Slide,
        [double]$X,
        [double]$Y,
        [double]$W,
        [double]$H,
        [string]$Text,
        [double]$Size = 12,
        [int]$Color = 0x111111,
        [bool]$Bold = $false,
        [int]$Align = 1,
        [string]$Font = "Arial"
    )
    $tb = $Slide.Shapes.AddTextbox(1, $X, $Y, $W, $H)
    $tb.TextFrame2.TextRange.Text = $Text
    $tb.TextFrame2.MarginLeft = 0
    $tb.TextFrame2.MarginRight = 0
    $tb.TextFrame2.MarginTop = 0
    $tb.TextFrame2.MarginBottom = 0
    $tb.TextFrame2.VerticalAnchor = 3
    $tb.TextFrame2.TextRange.Font.Name = $Font
    $tb.TextFrame2.TextRange.Font.Size = $Size
    $tb.TextFrame2.TextRange.Font.Fill.ForeColor.RGB = $Color
    if ($Bold) { $tb.TextFrame2.TextRange.Font.Bold = $msoTrue }
    $tb.TextFrame2.TextRange.ParagraphFormat.Alignment = $Align
    return $tb
}

function Add-Arrow {
    param(
        $Slide,
        [double]$X1,
        [double]$Y1,
        [double]$X2,
        [double]$Y2,
        [int]$Color = 0x1F4E8C,
        [double]$Weight = 3.0
    )
    $line = $Slide.Shapes.AddLine($X1, $Y1, $X2, $Y2)
    $line.Line.ForeColor.RGB = $Color
    $line.Line.Weight = $Weight
    $line.Line.EndArrowheadStyle = 3
    return $line
}

function Add-IconText {
    param(
        $Slide,
        [double]$X,
        [double]$Y,
        [double]$W,
        [double]$H,
        [string]$Icon,
        [int]$Color = 0x1F4E8C
    )
    return Add-Text $Slide $X $Y $W $H $Icon 30 $Color $true 2 "Segoe UI Symbol"
}

function C {
    param([int]$R, [int]$G, [int]$B)
    return ($R + (256 * $G) + (65536 * $B))
}

function Add-Sidebar {
    param(
        $Slide,
        [double]$X,
        [double]$Y,
        [double]$W,
        [double]$H,
        [string]$Label,
        [string]$Icon,
        [int]$Fill
    )
    Add-Shape $Slide 5 $X $Y $W $H "" $Fill $Fill 0 | Out-Null
    Add-IconText $Slide ($X + 8) ($Y + 18) ($W - 16) 34 $Icon 0xFFFFFF | Out-Null
    Add-Text $Slide ($X + 8) ($Y + 64) ($W - 16) 34 $Label 11 0xFFFFFF $true 2 | Out-Null
}

function Add-MetricRow {
    param(
        $Slide,
        [double]$X,
        [double]$Y,
        [string]$Metric,
        [string]$CBR,
        [string]$KOTMA
    )
    $inkLocal = C 17 17 17
    $blueLocal = C 31 78 140
    $redLocal = C 201 31 85
    Add-Text $Slide $X $Y 135 18 $Metric 11 $inkLocal $false 1 | Out-Null
    Add-Text $Slide ($X + 210) $Y 45 18 $CBR 11 $blueLocal $true 2 | Out-Null
    Add-Arrow $Slide ($X + 285) ($Y + 9) ($X + 365) ($Y + 9) $redLocal 2.4 | Out-Null
    Add-Text $Slide ($X + 390) $Y 56 18 $KOTMA 11 $redLocal $true 2 | Out-Null
    $dash = $Slide.Shapes.AddLine($X, ($Y + 22), ($X + 470), ($Y + 22))
    $dash.Line.ForeColor.RGB = C 184 194 204
    $dash.Line.DashStyle = 4
    $dash.Line.Weight = 0.6
}

$resolved = [System.IO.Path]::GetFullPath($OutputPath)
$dir = [System.IO.Path]::GetDirectoryName($resolved)
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
if (Test-Path -LiteralPath $resolved) {
    $backup = [System.IO.Path]::Combine($dir, "Fig1_KOTMA_SR_Graphical_Abstract_Editable.backup_$((Get-Date).ToString('yyyyMMdd_HHmmss')).pptx")
    Copy-Item -LiteralPath $resolved -Destination $backup
}

$ppt = $null
try {
    $ppt = New-Object -ComObject PowerPoint.Application
    $ppt.Visible = $msoTrue
    $pres = $ppt.Presentations.Add($msoTrue)
    $pres.PageSetup.SlideWidth = 1200
    $pres.PageSetup.SlideHeight = 800
    $slide = $pres.Slides.Add(1, $ppLayoutBlank)
    $slide.FollowMasterBackground = $msoFalse
    $slide.Background.Fill.ForeColor.RGB = 0xFFFFFF

    $black = C 0 0 0
    $ink = C 17 17 17
    $blue = C 31 78 140
    $blueLight = C 244 248 252
    $red = C 201 31 85
    $redLight = C 255 244 247
    $slate = C 47 61 74
    $slateLight = C 245 247 250
    $lineBlue = C 45 98 163
    $lineRed = C 221 110 136
    $softBlueLine = C 166 194 230
    $softRedLine = C 229 160 179
    $softSlateLine = C 166 183 199
    $muted = C 184 194 204
    $white = C 255 255 255

    Add-Text $slide 90 10 1020 28 "KOTMA-SR: knowledge-guided first-article recommendation under sparse industrial histories" 22 $black $true 2 "Arial Narrow" | Out-Null

    # Section 1
    Add-Shape $slide 5 8 50 1184 90 "" (C 251 253 255) $softBlueLine 1.0 | Out-Null
    Add-Sidebar $slide 8 50 76 90 "Problem" "P" $blue
    Add-Text $slide 432 58 380 24 "1. Industrial context and decision objective" 18 $blue $true 2 "Arial" | Out-Null
    Add-Shape $slide 5 108 83 305 64 "Production context`nHigh-reliability manufacturing`nMulti-product, small-batch, mixed-line production" $blueLight $lineBlue 1.1 "Arial" 11 $ink $false 1 | Out-Null
    Add-Shape $slide 5 462 83 320 64 "Industrial constraint`nSparse historical PCB-side cases`nNo target-board feedback yet`nRepeated trial printing is undesirable" $blueLight $lineBlue 1.1 "Arial" 11 $ink $false 1 | Out-Null
    Add-Shape $slide 5 832 83 350 64 "Decision objective`nRapid first-article pressure recommendation`nExecutable setting for engineer verification" $blueLight $lineBlue 1.1 "Arial" 11 $ink $false 1 | Out-Null
    Add-Arrow $slide 412 115 452 115 $blue 4 | Out-Null
    Add-Arrow $slide 782 115 822 115 $blue 4 | Out-Null

    # Section 2
    Add-Shape $slide 5 8 185 1184 330 "" (C 255 252 253) $softRedLine 1.0 | Out-Null
    Add-Sidebar $slide 8 185 76 330 "Method" "M" $red
    Add-Text $slide 400 196 420 24 "2. Support-audited process-knowledge reasoning" 18 (C 158 18 62) $true 2 "Arial" | Out-Null
    Add-Shape $slide 5 98 270 120 102 "New PCB side`ndescriptor available`npad-field geometry available`nSPI outcome hidden" $white $lineBlue 1.0 "Arial" 11 $ink $false 1 | Out-Null
    Add-Shape $slide 5 284 225 232 70 "Descriptor memory`ndescriptor-based CBR`nauditable nearest-case retrieval`ndefault recommendation path" $blueLight $lineBlue 1.0 "Arial" 10.5 $ink $false 1 | Out-Null
    Add-Shape $slide 5 284 334 232 72 "Structural memory`nsuper-node coarsening`nFGW structure-aware matching`ncomplementary evidence" $redLight $lineRed 1.0 "Arial" 10.5 $ink $false 1 | Out-Null
    Add-Shape $slide 5 548 246 292 150 "Sparse-tail support audit`nif support is sufficient:`n  keep CBR default`nif support is weak (sparse tail):`n  allow bounded structural correction" (C 255 249 251) $red 1.4 "Arial" 12 $ink $false 1 | Out-Null
    Add-Shape $slide 5 538 416 312 48 "final pressure = round_0.1(`nCBR pressure + capped structural adjustment )" $white (C 226 93 122) 1.0 "Arial" 10.5 $ink $false 2 | Out-Null
    Add-Shape $slide 5 892 220 282 275 "" (C 249 251 254) $lineBlue 1.0 | Out-Null
    Add-Shape $slide 5 892 220 282 54 "Engineer-facing`nrecommendation card" $blue $blue 0.0 "Arial" 12 0xFFFFFF $true 2 | Out-Null
    $cardRows = @(
        @("Recommended pressure:", "6.2"),
        @("Velocity suggestion:", "0.8"),
        @("Source:", "CBR default / bounded correction"),
        @("Top neighbors:", "A05, A02, A03"),
        @("Interval:", "6.1-6.3"),
        @("Review flag:", "yes/no"),
        @("Reason:", "sparse tail / weak support / OOD")
    )
    $y = 286
    foreach ($row in $cardRows) {
        Add-Text $slide 905 $y 135 16 $row[0] 10 $blue $true 1 | Out-Null
        Add-Text $slide 1060 $y 98 16 $row[1] 10 0x111111 $false 1 | Out-Null
        $rule = $slide.Shapes.AddLine(902, ($y + 18), 1162, ($y + 18))
        $rule.Line.ForeColor.RGB = C 192 205 217
        $rule.Line.DashStyle = 4
        $rule.Line.Weight = 0.6
        $y += 28
    }
    Add-Arrow $slide 218 322 276 322 $blue 4 | Out-Null
    Add-Arrow $slide 218 322 276 260 $blue 3 | Out-Null
    Add-Arrow $slide 218 322 276 370 $blue 3 | Out-Null
    Add-Arrow $slide 516 260 540 295 $blue 3 | Out-Null
    Add-Arrow $slide 516 370 540 344 $blue 3 | Out-Null
    Add-Arrow $slide 840 320 884 320 $blue 4 | Out-Null

    # Section 3
    Add-Shape $slide 5 8 545 1184 220 "" (C 250 251 252) $softSlateLine 1.0 | Out-Null
    Add-Sidebar $slide 8 545 76 220 "Claim" "C" $slate
    Add-Text $slide 406 555 420 24 "3. Retrospective evidence and bounded claim" 18 $blue $true 2 "Arial" | Out-Null
    Add-Shape $slide 5 98 592 518 150 "" $white $lineBlue 1.0 | Out-Null
    Add-Text $slide 165 605 160 18 "Performance summary" 13 $blue $true 1 | Out-Null
    Add-Text $slide 400 605 45 18 "CBR" 11 $blue $true 2 | Out-Null
    Add-Text $slide 462 605 25 18 "->" 15 $blue $true 2 "Arial" | Out-Null
    Add-Text $slide 510 605 80 18 "KOTMA-SR" 11 $red $true 2 | Out-Null
    Add-MetricRow $slide 112 635 "MAE" "0.324" "0.265"
    Add-MetricRow $slide 112 660 "Median error" "0.4" "0.1"
    Add-MetricRow $slide 112 685 "Within +/-0.2" "41.2%" "55.9%"
    Add-MetricRow $slide 112 710 "Within +/-0.4" "73.5%" "79.4%"
    Add-Shape $slide 5 640 592 530 150 "Evidence boundary`n- Retrospective recovery of historical engineering settings`n- Supports engineer-supervised verification`n- Reduces MAE relative to CBR in the current database`n- Not autonomous quality optimization`n- Not external deployment validation" $white $lineBlue 1.0 "Arial" 11 $ink $false 1 | Out-Null

    $pres.SaveAs($resolved, $ppSaveAsOpenXMLPresentation)
    Write-Output "Saved editable PowerPoint: $resolved"
    Write-Output "Slides: $($pres.Slides.Count)"
    $pres.Close()
}
finally {
    if ($ppt -ne $null) {
        $ppt.Quit()
        [System.Runtime.InteropServices.Marshal]::ReleaseComObject($ppt) | Out-Null
    }
}
