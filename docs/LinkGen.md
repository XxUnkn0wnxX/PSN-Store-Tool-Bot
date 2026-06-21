# LinkGen

[`LinkGen.py`](../LinkGen.py) resolves a PlayStation product ID into its full
regional SKU and generates a Sony checkout link.

The script does not read or send PlayStation cookies. Authentication happens
in your browser after opening the generated link.

## Requirements

- Python 3
- An internet connection
- A browser signed in to the [PlayStation Store](https://store.playstation.com/)

The script uses only Python's standard library.

## Interactive mode

Run:

```bash
python3 LinkGen.py
```

The script asks for a region and then accepts one product ID per line. Submit
one blank line after the final product ID to generate the checkout links.

Backspace and Delete edit the current line. Pressing Backspace on an empty line
restores the previous product ID so it can be corrected or removed.

You can preset the region:

```bash
python3 LinkGen.py --region au
```

## Source-file mode

Create a text file containing one product ID per line:

```text
EP4015-NPEB00982_00-AVAGARESTG000028
EP1063-BLES01788_00-AVHYPERDIM000019
```

Run:

```bash
python3 LinkGen.py --region au --src product_ids.txt
```

`--region` is required with `--src`. Source-file mode does not prompt for
input.

## Saving links to a file

Use `--out` to save successful links to a text file:

```bash
python3 LinkGen.py --region au --src product_ids.txt --out links.txt
```

The output file contains one link per line without blank lines. When any
products fail, their IDs are appended under a `Failed SKUs:` section. Successful
links are not repeated in the terminal when `--out` is used.

## Help

Show command help:

```bash
python3 LinkGen.py --help
```

Show every supported region and short alias:

```bash
python3 LinkGen.py --help region
```

## Input and output

The preferred input is the base product ID:

```text
EP4015-NPEB00982_00-AVAGARESTG000028
```

An already resolved SKU such as the following is also accepted:

```text
EP4015-NPEB00982_00-AVAGARESTG000028-E001
```

The script asks Sony for the region-specific SKU suffix and prints full links
under `Add To Cart Links`:

```text
https://checkout.playstation.com/add/EP4015-NPEB00982_00-AVAGARESTG000028-E001?clientId=2eb25762-877f-4140-b341-7c7e14c19f98
```

Products that cannot be resolved are listed under `Failed SKUs:` after the
successful links.

## Supported countries and regions

A short alias selects the default locale shown below. For countries with
multiple Store languages, pass any locale from the last column to select a
different language.

| Alias | Country | Default locale | Supported locales |
| --- | --- | --- | --- |
| `ar` | Argentina | `es-AR` | `en-AR`, `es-AR` |
| `au` | Australia | `en-AU` | `en-AU` |
| `at` | Austria | `de-AT` | `de-AT` |
| `bh` | Bahrain | `ar-BH` | `ar-BH`, `en-BH` |
| `be` | Belgium | `nl-BE` | `fr-BE`, `nl-BE` |
| `br` | Brazil | `pt-BR` | `en-BR`, `es-BR`, `pt-BR` |
| `bg` | Bulgaria | `en-BG` | `en-BG` |
| `ca` | Canada | `en-CA` | `en-CA`, `fr-CA` |
| `cl` | Chile | `es-CL` | `en-CL`, `es-CL` |
| `cn` | China | `zh-CN` | `zh-CN` |
| `co` | Colombia | `es-CO` | `en-CO`, `es-CO` |
| `cr` | Costa Rica | `es-CR` | `en-CR`, `es-CR` |
| `hr` | Croatia | `en-HR` | `en-HR` |
| `cy` | Cyprus | `en-CY` | `en-CY` |
| `cz` | Czechia | `cs-CZ` | `cs-CZ`, `en-CZ` |
| `dk` | Denmark | `da-DK` | `da-DK`, `en-DK` |
| `ec` | Ecuador | `es-EC` | `en-EC`, `es-EC` |
| `sv` | El Salvador | `es-SV` | `es-SV` |
| `fi` | Finland | `fi-FI` | `en-FI`, `fi-FI` |
| `fr` | France | `fr-FR` | `fr-FR` |
| `de` | Germany | `de-DE` | `de-DE` |
| `gr` | Greece | `el-GR` | `el-GR`, `en-GR` |
| `gt` | Guatemala | `es-GT` | `es-GT` |
| `hn` | Honduras | `es-HN` | `es-HN` |
| `hk` | Hong Kong | `zh-HK` | `ch-HK`, `en-HK`, `zh-HK` |
| `hu` | Hungary | `hu-HU` | `en-HU`, `hu-HU` |
| `is` | Iceland | `en-IS` | `en-IS` |
| `in` | India | `en-IN` | `en-IN` |
| `id` | Indonesia | `id-ID` | `en-ID`, `id-ID` |
| `il` | Israel | `en-IL` | `en-IL` |
| `it` | Italy | `it-IT` | `it-IT` |
| `jp` | Japan | `ja-JP` | `ja-JP` |
| `kw` | Kuwait | `ar-KW` | `ar-KW`, `en-KW` |
| `lb` | Lebanon | `ar-LB` | `ar-LB`, `en-LB` |
| `lu` | Luxembourg | `fr-LU` | `de-LU`, `fr-LU` |
| `my` | Malaysia | `en-MY` | `en-MY` |
| `mt` | Malta | `en-MT` | `en-MT` |
| `mx` | Mexico | `es-MX` | `en-MX`, `es-MX` |
| `nl` | Netherlands | `nl-NL` | `nl-NL` |
| `nz` | New Zealand | `en-NZ` | `en-NZ` |
| `no` | Norway | `no-NO` | `en-NO`, `no-NO` |
| `om` | Oman | `ar-OM` | `ar-OM`, `en-OM` |
| `pa` | Panama | `es-PA` | `en-PA`, `es-PA` |
| `py` | Paraguay | `es-PY` | `es-PY` |
| `pe` | Peru | `es-PE` | `en-PE`, `es-PE` |
| `pl` | Poland | `pl-PL` | `en-PL`, `pl-PL` |
| `pt` | Portugal | `pt-PT` | `pt-PT` |
| `qa` | Qatar | `ar-QA` | `ar-QA`, `en-QA` |
| `ro` | Romania | `ro-RO` | `en-RO`, `ro-RO` |
| `ru` | Russia | `ru-RU` | `ru-RU` |
| `sa` | Saudi Arabia | `ar-SA` | `ar-SA`, `en-SA` |
| `sg` | Singapore | `en-SG` | `en-SG` |
| `sk` | Slovakia | `en-SK` | `en-SK` |
| `si` | Slovenia | `en-SI` | `en-SI` |
| `za` | South Africa | `en-ZA` | `en-ZA` |
| `kr` | South Korea | `ko-KR` | `ko-KR` |
| `es` | Spain | `es-ES` | `en-ES`, `es-ES` |
| `se` | Sweden | `sv-SE` | `en-SE`, `sv-SE` |
| `ch` | Switzerland | `de-CH` | `de-CH`, `fr-CH`, `it-CH` |
| `tw` | Taiwan | `zh-TW` | `ch-TW`, `en-TW`, `zh-TW` |
| `th` | Thailand | `th-TH` | `en-TH`, `th-TH` |
| `tr` | Türkiye | `tr-TR` | `en-TR`, `tr-TR` |
| `ua` | Ukraine | `ru-UA` | `ru-UA` |
| `ae` | United Arab Emirates | `ar-AE` | `ar-AE`, `en-AE` |
| `gb`, `uk` | United Kingdom | `en-GB` | `en-GB` |
| `us` | United States | `en-US` | `en-US` |
| `vn` | Vietnam | `vi-VN` | `vi-VN` |

## Notes

- The generated URL does not contain account credentials.
- The browser must be signed in to the PlayStation Store.
- The PlayStation account region should match the selected region.
- Sony may reject products that are unavailable or cannot be entitled to the
  current account.
