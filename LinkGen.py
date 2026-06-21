#!/usr/bin/env python3

import argparse
import json
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote
from urllib.request import Request, urlopen


CLIENT_ID = "2eb25762-877f-4140-b341-7c7e14c19f98"
CHECKOUT_BASE_URL = "https://checkout.playstation.com/add"
LOOKUP_BASE_URL = (
    "https://store.playstation.com/store/api/chihiro/"
    "00_09_000/container"
)

VALID_REGIONS = [
    "ar-AE", "ar-BH", "ar-KW", "ar-LB", "ar-OM", "ar-QA", "ar-SA", "ch-HK",
    "ch-TW", "cs-CZ", "da-DK", "de-AT", "de-CH", "de-DE", "de-LU", "el-GR",
    "en-AE", "en-AR", "en-AU", "en-BG", "en-BH", "en-BR", "en-CA", "en-CL",
    "en-CO", "en-CR", "en-CY", "en-CZ", "en-DK", "en-EC", "en-ES", "en-FI",
    "en-GB", "en-GR", "en-HK", "en-HR", "en-HU", "en-ID", "en-IL", "en-IN",
    "en-IS", "en-KW", "en-LB", "en-MT", "en-MX", "en-MY", "en-NO", "en-NZ",
    "en-OM", "en-PA", "en-PE", "en-PL", "en-QA", "en-RO", "en-SA", "en-SE",
    "en-SG", "en-SI", "en-SK", "en-TH", "en-TR", "en-TW", "en-US", "en-ZA",
    "es-AR", "es-BR", "es-CL", "es-CO", "es-CR", "es-EC", "es-ES", "es-GT",
    "es-HN", "es-MX", "es-PA", "es-PE", "es-PY", "es-SV", "fi-FI", "fr-BE",
    "fr-CA", "fr-CH", "fr-FR", "fr-LU", "hu-HU", "id-ID", "it-CH", "it-IT",
    "ja-JP", "ko-KR", "nl-BE", "nl-NL", "no-NO", "pl-PL", "pt-BR", "pt-PT",
    "ro-RO", "ru-RU", "ru-UA", "sv-SE", "th-TH", "tr-TR", "vi-VN", "zh-CN",
    "zh-HK", "zh-TW",
]

COUNTRY_OVERRIDES = {
    "AE": "ar-AE",
    "AR": "es-AR",
    "AT": "de-AT",
    "AU": "en-AU",
    "BE": "nl-BE",
    "BH": "ar-BH",
    "BG": "en-BG",
    "BR": "pt-BR",
    "CA": "en-CA",
    "CH": "de-CH",
    "CL": "es-CL",
    "CN": "zh-CN",
    "CO": "es-CO",
    "CR": "es-CR",
    "CY": "en-CY",
    "CZ": "cs-CZ",
    "DE": "de-DE",
    "DK": "da-DK",
    "EC": "es-EC",
    "FR": "fr-FR",
    "FI": "fi-FI",
    "GB": "en-GB",
    "GR": "el-GR",
    "GT": "es-GT",
    "HK": "zh-HK",
    "HN": "es-HN",
    "HR": "en-HR",
    "HU": "hu-HU",
    "ID": "id-ID",
    "IL": "en-IL",
    "IN": "en-IN",
    "IS": "en-IS",
    "ES": "es-ES",
    "IT": "it-IT",
    "JP": "ja-JP",
    "KR": "ko-KR",
    "KW": "ar-KW",
    "LB": "ar-LB",
    "LU": "fr-LU",
    "MT": "en-MT",
    "MX": "es-MX",
    "MY": "en-MY",
    "NL": "nl-NL",
    "NO": "no-NO",
    "NZ": "en-NZ",
    "OM": "ar-OM",
    "PA": "es-PA",
    "PE": "es-PE",
    "PL": "pl-PL",
    "PT": "pt-PT",
    "PY": "es-PY",
    "QA": "ar-QA",
    "RO": "ro-RO",
    "RU": "ru-RU",
    "SA": "ar-SA",
    "SE": "sv-SE",
    "SG": "en-SG",
    "SI": "en-SI",
    "SK": "en-SK",
    "SV": "es-SV",
    "TH": "th-TH",
    "TR": "tr-TR",
    "TW": "zh-TW",
    "UA": "ru-UA",
    "UK": "en-GB",
    "US": "en-US",
    "VN": "vi-VN",
    "ZA": "en-ZA",
}

FULL_SKU_SUFFIX_RE = re.compile(r"^(?P<product>.+)-[A-Z]\d{3}$", re.IGNORECASE)


def print_region_help() -> None:
    print("Supported region codes:\n")
    for index in range(0, len(VALID_REGIONS), 6):
        print("  " + "  ".join(VALID_REGIONS[index:index + 6]))

    print("\nSupported short aliases:\n")
    aliases = [f"{alias.lower()}={region}" for alias, region in COUNTRY_OVERRIDES.items()]
    for index in range(0, len(aliases), 6):
        print("  " + "  ".join(aliases[index:index + 6]))


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Resolve regional PlayStation SKUs and generate checkout links. "
            "No cookies or PlayStation credentials are used."
        ),
        epilog=(
            "Examples:\n"
            "  python3 LinkGen.py\n"
            "  python3 LinkGen.py --help region\n"
            "  python3 LinkGen.py --region au\n"
            "  python3 LinkGen.py --region en-US\n"
            "  python3 LinkGen.py --region au --src product_ids.txt\n"
            "  python3 LinkGen.py --region au --src product_ids.txt "
            "--out links.txt"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--region",
        metavar="REGION",
        help="Region alias or locale, for example: au, us, gb, en-AU, en-US.",
    )
    parser.add_argument(
        "--src",
        metavar="PATH",
        help="Read product IDs from a text file. Requires --region.",
    )
    parser.add_argument(
        "--out",
        metavar="PATH",
        help="Save successful add-to-cart links to a text file.",
    )
    return parser.parse_args()


def normalize_region(value: str) -> str:
    candidate = value.strip()
    if not candidate:
        raise ValueError("Region is required.")

    for region in VALID_REGIONS:
        if region.lower() == candidate.lower():
            return region

    upper = candidate.upper()
    if upper in COUNTRY_OVERRIDES:
        return COUNTRY_OVERRIDES[upper]

    if len(upper) == 2:
        preferred = f"en-{upper}"
        if preferred in VALID_REGIONS:
            return preferred
        for region in VALID_REGIONS:
            if region.upper().endswith(f"-{upper}"):
                return region

    raise ValueError(
        f"Invalid region '{value}'. Use a two-letter alias such as au/us/gb "
        "or a full locale such as en-AU/en-US/fr-FR."
    )


def prompt_for_region() -> str:
    while True:
        try:
            return normalize_region(input("Region: "))
        except EOFError:
            raise SystemExit("\nNo region provided.")
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)


def collect_product_ids() -> list[str]:
    print(
        "Enter one product ID per line. Submit a blank line to generate the "
        "links:"
    )

    if sys.stdin.isatty():
        try:
            return collect_product_ids_from_terminal()
        except (ImportError, OSError):
            pass

    product_ids: list[str] = []

    while True:
        try:
            line = input()
        except EOFError:
            break

        value = line.strip()
        if not value:
            break

        product_ids.append(value)

    return product_ids


def collect_product_ids_from_terminal() -> list[str]:
    import termios
    import tty

    product_ids: list[str] = []
    current: list[str] = []
    file_descriptor = sys.stdin.fileno()
    original_settings = termios.tcgetattr(file_descriptor)

    def erase_character() -> None:
        if current:
            current.pop()
            sys.stdout.write("\b \b")
            sys.stdout.flush()
        elif product_ids:
            current.extend(product_ids.pop())
            sys.stdout.write("\033[1A\r\033[2K")
            sys.stdout.write("".join(current))
            sys.stdout.flush()

    try:
        tty.setraw(file_descriptor)
        while True:
            character = sys.stdin.read(1)

            if character in {"\r", "\n"}:
                value = "".join(current).strip()
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                if not value:
                    break
                product_ids.append(value)
                current.clear()
                continue

            if character in {"\x08", "\x7f"}:
                erase_character()
                continue

            if character == "\x1b":
                sequence = sys.stdin.read(1)
                if sequence == "[":
                    key = sys.stdin.read(1)
                    if key == "3" and sys.stdin.read(1) == "~":
                        erase_character()
                continue

            if character == "\x03":
                raise KeyboardInterrupt

            if character == "\x04":
                sys.stdout.write("\r\n")
                sys.stdout.flush()
                value = "".join(current).strip()
                if value:
                    product_ids.append(value)
                break

            if character == "\x15":
                while current:
                    erase_character()
                continue

            if character.isprintable():
                current.append(character)
                sys.stdout.write(character)
                sys.stdout.flush()
    finally:
        termios.tcsetattr(file_descriptor, termios.TCSADRAIN, original_settings)

    return product_ids


def load_product_ids(path: str) -> list[str]:
    try:
        with open(path, encoding="utf-8") as handle:
            return [line.strip() for line in handle if line.strip()]
    except OSError as exc:
        raise ValueError(f"Unable to read source file '{path}': {exc}") from exc


def save_results(
    path: str,
    links: list[str],
    failures: list[tuple[str, str]],
) -> None:
    try:
        with open(path, "w", encoding="utf-8") as handle:
            if links:
                handle.write("\n".join(links))
                handle.write("\n")

            if failures:
                if links:
                    handle.write("\n")
                handle.write("Failed SKUs:\n")
                handle.write("\n".join(product_id for product_id, _ in failures))
                handle.write("\n")
    except OSError as exc:
        raise ValueError(f"Unable to write output file '{path}': {exc}") from exc


def normalize_product_id(value: str) -> str:
    product_id = value.strip().upper()
    match = FULL_SKU_SUFFIX_RE.fullmatch(product_id)
    if match and match.group("product").count("-") == 2:
        product_id = match.group("product")

    if product_id.count("-") != 2 or "_" not in product_id:
        raise ValueError("Invalid product ID format.")

    return product_id


def resolve_regional_sku(product_id: str, region: str) -> str:
    language, country = region.split("-", 1)
    encoded_product_id = quote(product_id, safe="-_")
    lookup_url = (
        f"{LOOKUP_BASE_URL}/{country}/{language}/19/{encoded_product_id}/"
    )
    request = Request(
        lookup_url,
        headers={
            "Accept": "application/json",
            "Accept-Language": region,
            "Origin": "https://checkout.playstation.com",
            "User-Agent": "PSN-LinkGen/1.0",
        },
    )

    try:
        with urlopen(request, timeout=20) as response:
            payload = json.load(response)
    except HTTPError as exc:
        if exc.code == 404:
            raise ValueError("Product was not found in this region.") from exc
        raise ValueError(f"PlayStation lookup failed with HTTP {exc.code}.") from exc
    except URLError as exc:
        reason = getattr(exc, "reason", exc)
        raise ValueError(f"Unable to contact PlayStation: {reason}") from exc
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError("PlayStation returned an invalid response.") from exc

    full_sku = payload.get("default_sku", {}).get("id")
    if not isinstance(full_sku, str) or not full_sku:
        message = payload.get("cause") or "No regional SKU was returned."
        raise ValueError(str(message))

    return full_sku


def build_checkout_url(full_sku: str) -> str:
    encoded_sku = quote(full_sku, safe="-_")
    return f"{CHECKOUT_BASE_URL}/{encoded_sku}?clientId={CLIENT_ID}"


def main() -> int:
    if sys.argv[1:] == ["--help", "region"]:
        print_region_help()
        return 0

    args = parse_args()

    if args.src and not args.region:
        print("Error: --region is required when using --src.", file=sys.stderr)
        return 2

    if args.region:
        try:
            region = normalize_region(args.region)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
    else:
        region = prompt_for_region()

    if args.src:
        try:
            product_ids = load_product_ids(args.src)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2
    else:
        product_ids = collect_product_ids()

    if not product_ids:
        source = f"source file '{args.src}'" if args.src else "input"
        print(f"No product IDs were found in {source}.", file=sys.stderr)
        return 1

    checkout_links: list[str] = []
    failures: list[tuple[str, str]] = []

    for original_value in product_ids:
        try:
            product_id = normalize_product_id(original_value)
            full_sku = resolve_regional_sku(product_id, region)
            checkout_links.append(build_checkout_url(full_sku))
        except ValueError as exc:
            failures.append((original_value, str(exc)))

    if args.out:
        try:
            save_results(args.out, checkout_links, failures)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            return 2

    if checkout_links and not args.out:
        print("\nAdd To Cart Links:\n")
        print("\n\n".join(checkout_links))

    if failures and not args.out:
        print("\nFailed SKUs:\n")
        for product_id, reason in failures:
            print(f"{product_id} — {reason}")

    return 0 if checkout_links else 1


if __name__ == "__main__":
    raise SystemExit(main())
