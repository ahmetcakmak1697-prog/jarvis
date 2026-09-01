# codex_verdict.ps1 -- Codex denetim ciktisindan verdict'i cozer.
#
# Ayri dosyada olmasinin TEK sebebi test edilebilirlik: bu fonksiyon otonom
# dongunun kapisidir (PASS -> devam, CONCERN/BLOCKER -> Ahmet'e git). Yanlis
# cozumlenirse dongu ya sahte onayla ilerler ya da hic ilerlemez.
#
# Kullanim:
#   . "$PSScriptRoot\codex_verdict.ps1"
#   Get-CodexVerdict -Cikti $ham -YankilananTalimat $tamTalimat

function Get-CodexVerdict {
    param(
        # codex CLI'nin tam konsol ciktisi.
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$Cikti,

        # Codex'e GONDERDIGIMIZ talimat. codex CLI prompt'u ciktiya yankilar;
        # talimat "BLOCKER" kelimesini 3, "PASS" kelimesini 2 kez icerdigi icin
        # yanki cikarilmazsa her denetim BLOCKER gorunur.
        [Parameter(Mandatory = $true)]
        [AllowEmptyString()]
        [string]$YankilananTalimat
    )

    $metin = $Cikti -replace "`r`n", "`n"
    if ($YankilananTalimat) {
        $metin = $metin.Replace(($YankilananTalimat -replace "`r`n", "`n"), "")
    }

    # 1) Acik karar satiri: "Verdict: PASS", "**VERDICT: BLOCKER**", "- verdict = CONCERN"
    #    Birden fazla varsa SONUNCUSU gecerli -- karar metnin sonunda yazilir.
    $acik = [regex]::Matches($metin, '(?im)^[\s>*_#-]*verdict[\s*_]*[:=][\s*_]*(PASS|CONCERN|BLOCKER)\b')
    if ($acik.Count -gt 0) {
        return $acik[$acik.Count - 1].Groups[1].Value.ToUpper()
    }

    # 2) Yedek: metinde tek basina duran SON karar kelimesi.
    $yedek = [regex]::Matches($metin, '\b(BLOCKER|CONCERN|PASS)\b')
    if ($yedek.Count -gt 0) {
        return $yedek[$yedek.Count - 1].Groups[1].Value.ToUpper()
    }

    # 3) Karar yok. Sessizce PASS'e dusmek yasak -- cagiran bunu hata sayar.
    return "BELIRSIZ"
}
