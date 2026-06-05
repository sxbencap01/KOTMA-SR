param(
    [string]$OutputPath = "D:\smt\predictionprocess202603\OTMA_KBS_CurrentDB_Final_KOTMASR_20260603\KOTMA-SR_Fig1-9_Editable_Visio.vsdx"
)

$ErrorActionPreference = "Stop"

function Set-CellFormula($shape, [string]$cellName, [string]$formula) {
    try { $shape.CellsU($cellName).FormulaU = $formula } catch {}
}

function Add-Box($page, [double]$x1, [double]$y1, [double]$x2, [double]$y2, [string]$text, [string]$fill, [string]$line = "RGB(38,50,56)") {
    $shape = $page.DrawRectangle($x1, $y1, $x2, $y2)
    $shape.Text = $text
    Set-CellFormula $shape "FillForegnd" $fill
    Set-CellFormula $shape "LineColor" $line
    Set-CellFormula $shape "LineWeight" "1.1 pt"
    Set-CellFormula $shape "Char.Size" "9 pt"
    Set-CellFormula $shape "Para.HorzAlign" "1"
    Set-CellFormula $shape "VerticalAlign" "1"
    return $shape
}

function Add-Label($page, [double]$x, [double]$y, [double]$w, [double]$h, [string]$text, [string]$color = "RGB(38,50,56)", [string]$size = "12 pt", [string]$bold = "1") {
    $shape = $page.DrawRectangle($x, $y, $x + $w, $y + $h)
    $shape.Text = $text
    Set-CellFormula $shape "FillPattern" "0"
    Set-CellFormula $shape "LinePattern" "0"
    Set-CellFormula $shape "Char.Color" $color
    Set-CellFormula $shape "Char.Size" $size
    Set-CellFormula $shape "Char.Style" $bold
    Set-CellFormula $shape "Para.HorzAlign" "1"
    Set-CellFormula $shape "VerticalAlign" "1"
    return $shape
}

function Add-Arrow($page, [double]$x1, [double]$y1, [double]$x2, [double]$y2, [string]$color = "RGB(38,50,56)") {
    $line = $page.DrawLine($x1, $y1, $x2, $y2)
    Set-CellFormula $line "LineColor" $color
    Set-CellFormula $line "LineWeight" "1.35 pt"
    Set-CellFormula $line "EndArrow" "13"
    return $line
}

function Add-Bar($page, [double]$x, [double]$y, [double]$w, [double]$h, [string]$label, [string]$value, [string]$fill) {
    Add-Label $page ($x - 1.9) ($y - 0.06) 1.75 0.22 $label "RGB(38,50,56)" "8 pt" "0" | Out-Null
    Add-Box $page $x $y ($x + $w) ($y + $h) $value $fill | Out-Null
}

function Setup-Page($page, [string]$name) {
    $page.Name = $name
    $page.PageSheet.CellsU("PageWidth").FormulaU = "16.5 in"
    $page.PageSheet.CellsU("PageHeight").FormulaU = "9.5 in"
}

$blue = "RGB(220,232,245)"
$blueStrong = "RGB(36,90,154)"
$red = "RGB(244,217,220)"
$redStrong = "RGB(176,58,72)"
$neutral = "RGB(232,237,242)"
$neutralStrong = "RGB(142,154,166)"
$ink = "RGB(38,50,56)"

try {
    $app = [Runtime.InteropServices.Marshal]::GetActiveObject("Visio.Application")
} catch {
    $app = New-Object -ComObject Visio.Application
}
$app.Visible = $true
$doc = $app.Documents.Add("")

# Fig1
$p = $doc.Pages.Item(1)
Setup-Page $p "Fig1 Graphical Abstract"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig1. KOTMA-SR: knowledge-guided first-article recommendation under sparse histories" $ink "16 pt" | Out-Null
Add-Box $p 0.55 6.15 2.95 7.55 "Sparse PCB cases`none executed setting`nper PCB side" $blue | Out-Null
Add-Box $p 3.45 6.15 5.9 7.55 "New PCB side`ngeometry known;`nSPI hidden" $neutral | Out-Null
Add-Box $p 6.55 6.65 9.05 7.55 "Case memory`ndescriptor recall" $blue | Out-Null
Add-Box $p 6.55 5.25 9.05 6.15 "Structural memory`nFGW re-ranking" $red | Out-Null
Add-Box $p 9.8 5.9 12.25 6.95 "Selection gate`nbounded tail correction`nor CBR default" $red | Out-Null
Add-Box $p 13.0 5.65 15.9 7.2 "Recommendation card`npressure 6.2`nvelocity 0.8`nverify 6.1-6.3" $blue | Out-Null
Add-Arrow $p 5.9 6.85 6.55 7.1 | Out-Null
Add-Arrow $p 5.9 6.55 6.55 5.7 | Out-Null
Add-Arrow $p 9.05 7.1 9.8 6.55 | Out-Null
Add-Arrow $p 9.05 5.7 9.8 6.3 | Out-Null
Add-Arrow $p 12.25 6.45 13.0 6.45 | Out-Null
Add-Box $p 1.0 2.75 4.4 4.25 "Pressure MAE`nCBR 0.324`nKOTMA-SR 0.265`n18.2% lower" $neutral | Out-Null
Add-Box $p 4.85 2.75 8.25 4.25 "Median error`nCBR 0.4`nKOTMA-SR 0.1`n75.0% lower" $neutral | Out-Null
Add-Box $p 8.7 2.75 12.1 4.25 "Within +/-0.2`nCBR 41.2%`nKOTMA-SR 55.9%`n+14.7 pp" $neutral | Out-Null
Add-Box $p 12.55 2.75 15.95 4.25 "Within +/-0.4`nCBR 73.5%`nKOTMA-SR 79.4%`n+5.9 pp" $neutral | Out-Null
Add-Label $p 2.1 1.55 12.6 0.35 "Retrospective decision support for rapid verification; not autonomous quality optimization" "RGB(82,97,107)" "10 pt" "0" | Out-Null

# Fig2
$p = $doc.Pages.Add(); Setup-Page $p "Fig2 Knowledge Architecture"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig2. Layered knowledge architecture" $ink "16 pt" | Out-Null
Add-Box $p 0.8 6.65 3.0 7.55 "Inputs`nPCB geometry`nprocess policy`nhistorical cases" $neutral | Out-Null
Add-Box $p 3.75 6.65 6.05 7.55 "Representation`ndescriptor memory`nprocess graph" $blue | Out-Null
Add-Box $p 6.8 6.65 9.05 7.55 "Memory alignment`nCBR recall`nFGW distance" $red | Out-Null
Add-Box $p 9.8 6.65 12.1 7.55 "Selective reasoning`ncommon support: CBR`nsparse tail: bounded correction" $red | Out-Null
Add-Box $p 12.85 6.65 15.25 7.55 "Output`npressure`nvelocity anchor`nreview card" $blue | Out-Null
Add-Arrow $p 3.0 7.1 3.75 7.1 | Out-Null
Add-Arrow $p 6.05 7.1 6.8 7.1 | Out-Null
Add-Arrow $p 9.05 7.1 9.8 7.1 | Out-Null
Add-Arrow $p 12.1 7.1 12.85 7.1 | Out-Null
Add-Box $p 2.0 4.65 5.0 5.65 "Auditable default`nDescriptor CBR remains the baseline decision path" $blue | Out-Null
Add-Box $p 5.65 4.65 9.35 5.65 "Sparse-tail reasoning`nStructural evidence is allowed only under weak local support" $red | Out-Null
Add-Box $p 10.0 4.65 13.85 5.65 "Trust layer`nIntervals, confidence, OOD and manual-review triggers" $neutral | Out-Null
Add-Label $p 1.7 2.8 13.2 0.5 "Conclusion: the method is not a black-box regressor; it is a layered case-memory system with bounded structural correction." $ink "11 pt" "0" | Out-Null

# Fig3
$p = $doc.Pages.Add(); Setup-Page $p "Fig3 Process Knowledge"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig3. Process knowledge and executable recommendation target" $ink "16 pt" | Out-Null
Add-Box $p 0.75 6.6 4.05 7.55 "Pressure is active`nExecutable range 5.0-8.0`n0.1 step allowed" $red | Out-Null
Add-Box $p 4.8 6.6 8.15 7.55 "Velocity is anchored`nObserved velocity is almost always 0.8`nEngineer override remains allowed" $blue | Out-Null
Add-Box $p 8.9 6.6 12.05 7.55 "A/B sides`nIndependent PCB-side decisions`nPhysical board grouping in validation" $neutral | Out-Null
Add-Box $p 12.8 6.6 15.75 7.55 "Historical memory`nPads, area and geometry descriptors`nSPI hidden at recommendation time" $neutral | Out-Null
Add-Label $p 1.2 4.65 14.0 0.35 "Reading: pressure is the recommendation variable; velocity is treated as an empirical process anchor." $ink "11 pt" "0" | Out-Null
Add-Bar $p 3.3 3.35 2.5 0.32 "pressure mass 5.6-6.4" "dominant" $red | Out-Null
Add-Bar $p 3.3 2.75 4.0 0.32 "velocity 0.8" "empirical anchor" $blue | Out-Null
Add-Bar $p 3.3 2.15 3.0 0.32 "board sides" "34 sides" $neutral | Out-Null
Add-Box $p 9.2 2.1 13.8 3.75 "Conclusion`nThe task is narrow and executable: recommend a usable first-article pressure for rapid verification, not optimize unseen quality." $neutral | Out-Null

# Fig4
$p = $doc.Pages.Add(); Setup-Page $p "Fig4 Structural Memory"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig4. Process-aware structural memory" $ink "16 pt" | Out-Null
Add-Box $p 0.8 6.55 3.1 7.5 "Raw descriptors`npads, area, side features" $blue | Out-Null
Add-Box $p 3.85 6.55 6.25 7.5 "Graph abstraction`nPCB super-nodes and local structure" $neutral | Out-Null
Add-Box $p 7.0 6.55 9.5 7.5 "FGW alignment`nstructure-aware distance" $red | Out-Null
Add-Box $p 10.25 6.55 12.75 7.5 "Re-ranked memory`ncase candidates" $red | Out-Null
Add-Box $p 13.45 6.55 15.75 7.5 "Bounded use`nonly sparse tails modify CBR" $blue | Out-Null
Add-Arrow $p 3.1 7.02 3.85 7.02 | Out-Null
Add-Arrow $p 6.25 7.02 7.0 7.02 | Out-Null
Add-Arrow $p 9.5 7.02 10.25 7.02 | Out-Null
Add-Arrow $p 12.75 7.02 13.45 7.02 | Out-Null
Add-Label $p 1.25 4.8 14.0 0.4 "Reading: this figure justifies the use of geometry/structure when descriptor-only recall is locally weak." $ink "11 pt" "0" | Out-Null
Add-Box $p 2.2 2.2 14.3 3.7 "Conclusion`nStructural memory supplies conditional evidence beyond tabular recall, but the final decision is bounded by executable process constraints and CBR support." $neutral | Out-Null

# Fig5
$p = $doc.Pages.Add(); Setup-Page $p "Fig5 Sparse Tail Gate"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig5. Sparse-tail bounded gate" $ink "16 pt" | Out-Null
Add-Box $p 0.9 6.65 3.05 7.5 "Descriptor CBR`nauditable nearest case" $blue | Out-Null
Add-Box $p 3.8 6.65 5.95 7.5 "Support audit`nfold-local pressure count" $neutral | Out-Null
Add-Box $p 6.8 7.0 9.35 7.75 "CBR default`nretain supported case" $blue | Out-Null
Add-Box $p 6.8 5.75 9.35 6.5 "Bounded correction`nFGW update <= 0.5" $red | Out-Null
Add-Box $p 10.3 6.4 12.75 7.1 "Executable grid`nround to 0.1 step" $red | Out-Null
Add-Arrow $p 3.05 7.08 3.8 7.08 | Out-Null
Add-Arrow $p 5.95 7.15 6.8 7.38 $blueStrong | Out-Null
Add-Arrow $p 5.95 6.95 6.8 6.12 $redStrong | Out-Null
Add-Arrow $p 9.35 7.38 10.3 6.85 | Out-Null
Add-Arrow $p 9.35 6.12 10.3 6.65 | Out-Null
Add-Bar $p 3.6 3.65 4.6 0.34 "CBR default" "27 sides" $blueStrong | Out-Null
Add-Bar $p 3.6 3.05 1.2 0.34 "bounded correction" "7 sides" $redStrong | Out-Null
Add-Box $p 9.0 2.75 14.0 4.05 "Sparse-tail mechanism`nCommon support: KOTMA-SR MAE 0.2667 equals CBR.`nSparse tail: KOTMA-SR 0.2571 vs CBR 0.5429." $neutral | Out-Null

# Fig6
$p = $doc.Pages.Add(); Setup-Page $p "Fig6 Validation System"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig6. Validation system" $ink "16 pt" | Out-Null
Add-Box $p 0.8 6.65 3.0 7.5 "Current database`n34 sides / 21 boards" $neutral | Out-Null
Add-Box $p 3.6 6.65 5.9 7.5 "Outer grouped LOBO`nhold out physical board" $blue | Out-Null
Add-Box $p 6.5 6.65 8.85 7.5 "Inner grouped tuning`nno held-out leakage" $red | Out-Null
Add-Box $p 9.45 6.65 11.9 7.5 "OOF calibration`nintervals and review gates" $red | Out-Null
Add-Box $p 12.5 6.65 15.45 7.5 "Held-out evaluation`nMAE, window hit rate, CI" $blue | Out-Null
Add-Arrow $p 3.0 7.08 3.6 7.08 | Out-Null
Add-Arrow $p 5.9 7.08 6.5 7.08 | Out-Null
Add-Arrow $p 8.85 7.08 9.45 7.08 | Out-Null
Add-Arrow $p 11.9 7.08 12.5 7.08 | Out-Null
Add-Box $p 1.2 3.65 4.3 4.85 "Baseline suite`nCBR, median, strong ML, OT variants, exploratory GNN" $blue | Out-Null
Add-Box $p 4.85 3.65 7.95 4.85 "Mechanism suite`nablation, sparse-tail, gate sensitivity" $red | Out-Null
Add-Box $p 8.5 3.65 11.6 4.85 "Trust suite`nbootstrap, calibration, review triggers" $red | Out-Null
Add-Box $p 12.15 3.65 15.25 4.85 "Robustness suite`nperturbation, sample efficiency, controls" $neutral | Out-Null
Add-Box $p 3.2 1.65 13.3 2.65 "Conclusion`nThe validation is retrospective and leakage-safe within the current database; temporal/external/prospective claims remain outside scope." $neutral | Out-Null

# Fig7
$p = $doc.Pages.Add(); Setup-Page $p "Fig7 Primary Results"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig7. Primary retrospective performance" $ink "16 pt" | Out-Null
Add-Bar $p 4.0 7.2 2.65 0.32 "KOTMA-SR" "MAE 0.265" $redStrong | Out-Null
Add-Bar $p 4.0 6.65 3.05 0.32 "Training median" "0.306" $neutralStrong | Out-Null
Add-Bar $p 4.0 6.1 3.15 0.32 "KOTMA-SR unconstrained" "0.315" "RGB(217,140,149)" | Out-Null
Add-Bar $p 4.0 5.55 3.24 0.32 "CBR" "0.324" $blueStrong | Out-Null
Add-Bar $p 4.0 5.0 4.24 0.32 "Training mode" "0.424" "RGB(180,190,202)" | Out-Null
Add-Box $p 8.8 6.1 12.3 7.45 "Paired CBR evidence`nmean gain 0.059`ncluster CI [0.016, 0.112]`nwin/tie/loss 6/27/1" $neutral | Out-Null
Add-Box $p 12.85 6.1 15.55 7.45 "Reviewer statement`nUse MAE as primary endpoint.`nDo not claim universal dominance." $red | Out-Null
Add-Box $p 2.4 2.55 14.1 3.8 "Conclusion`nKOTMA-SR obtains the best grouped retrospective MAE point estimate and significantly improves over Top-1 CBR by physical-board cluster bootstrap." $neutral | Out-Null

# Fig8
$p = $doc.Pages.Add(); Setup-Page $p "Fig8 Trust Calibration"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig8. Trustworthiness and review calibration" $ink "16 pt" | Out-Null
Add-Box $p 0.9 6.65 3.7 7.6 "Risk-coverage curve`ncoverage remains 1.0 at low thresholds`naccepted coverage 82.4%" $blue | Out-Null
Add-Box $p 4.35 6.65 7.15 7.6 "Interval calibration`n80% nominal -> 79.4% empirical`n90% nominal -> 85.3% empirical" $red | Out-Null
Add-Box $p 7.8 6.65 10.6 7.6 "Review triggers`nOOD distance`nretrieval-prior disagreement`nwide interval warning" $neutral | Out-Null
Add-Box $p 11.25 6.65 15.45 7.6 "Trust-aware card`nrecommendation + interval + evidence trace + manual-review flag" $blue | Out-Null
Add-Box $p 2.5 3.2 14.0 4.45 "Conclusion`nKOTMA-SR should be presented as a selective decision-support method: it recommends quickly when evidence is adequate and asks for review when support is weak." $neutral | Out-Null

# Fig9
$p = $doc.Pages.Add(); Setup-Page $p "Fig9 Evidence Matrix"
Add-Label $p 0.35 8.75 15.8 0.45 "Fig9. Evidence matrix and claim boundary" $ink "16 pt" | Out-Null
Add-Box $p 0.8 6.65 3.55 7.6 "Ablation`nSparse-tail correction improves over descriptor-only mechanism in bounded use." $red | Out-Null
Add-Box $p 4.1 6.65 6.85 7.6 "Perturbation`nrecommendations remain stable under descriptor perturbations." $blue | Out-Null
Add-Box $p 7.4 6.65 10.15 7.6 "Sample efficiency`nsmall-data protocol is explicitly evaluated." $neutral | Out-Null
Add-Box $p 10.7 6.65 13.45 7.6 "Negative controls`nclaim boundary is tested, not hidden." $neutral | Out-Null
Add-Box $p 1.4 3.55 5.4 4.75 "Allowed claim`nBest retrospective MAE point estimate; significant over CBR." $blue | Out-Null
Add-Box $p 6.0 3.55 10.5 4.75 "Limited claim`nStrong-baseline point estimates are favorable, but CIs can cross zero." $red | Out-Null
Add-Box $p 11.1 3.55 15.15 4.75 "Prohibited claim`nNo autonomous quality optimization or external deployment proof." $neutral | Out-Null
Add-Box $p 3.15 1.7 13.35 2.75 "Conclusion`nThe evidence matrix is what makes the paper reviewable: it states what is proven, what is promising, and what must remain future work." $neutral | Out-Null

$resolved = [System.IO.Path]::GetFullPath($OutputPath)
$dir = [System.IO.Path]::GetDirectoryName($resolved)
if (-not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Path $dir | Out-Null }
$doc.SaveAs($resolved)
$app.ActiveWindow.Page = $doc.Pages.Item(1)
Write-Output "Saved Visio document: $resolved"
Write-Output "Pages: $($doc.Pages.Count)"
