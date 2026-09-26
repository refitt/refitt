#!/usr/bin/env python3
"""Find host galaxies for one sky position or a CSV position list.

One position:
    python scripts/find_host.py --ra 321.8157 --dec 3.7980 --ps1-hats /catalogs/ps1

Position list (CSV columns: ``ra`` and either ``dec`` or ``declination``):
    python scripts/find_host.py --input positions.csv --ps1-hats /catalogs/ps1
"""
from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

# Let the script work directly from a source checkout as well as an installed
# environment. The package itself remains importable without script concerns.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from refitt_host import AssociationOptions, HostAssociator


def _associator(args: argparse.Namespace) -> HostAssociator:
    options = AssociationOptions(
        search_radius_arcsec=args.search_radius_arcsec, samples=args.samples, seed=args.seed,
        use_redshift=args.use_redshift, use_magnitude=args.use_magnitude, verbose=args.verbose,
    )
    if args.catalog == "ps1":
        return HostAssociator.ps1(args.ps1_hats, margin_cache_path=args.ps1_margin_cache, options=options)
    if args.catalog == "regalade":
        return HostAssociator.regalade(args.regalade_hats, margin_cache_path=args.regalade_margin_cache, options=options)
    return HostAssociator.local(
        ps1_path=args.ps1_hats, ps1_margin_cache_path=args.ps1_margin_cache,
        regalade_path=args.regalade_hats, regalade_margin_cache_path=args.regalade_margin_cache,
        options=options,
    )


def _add_catalog_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--catalog", choices=("ps1", "regalade", "both"), default="ps1")
    parser.add_argument("--ps1-hats", type=Path, help="Absolute path to a local PS1 HATS collection.")
    parser.add_argument("--ps1-margin-cache", type=Path)
    parser.add_argument("--regalade-hats", type=Path, help="Absolute path to a local REGLADE HATS collection.")
    parser.add_argument("--regalade-margin-cache", type=Path)
    parser.add_argument("--search-radius-arcsec", type=float, default=60.0)
    parser.add_argument("--samples", type=int, default=1000)
    parser.add_argument("--seed", type=int, default=1729)
    parser.add_argument("--use-redshift", action="store_true")
    parser.add_argument("--use-magnitude", action="store_true")
    parser.add_argument("--verbose", action="store_true", help="Show HATS query progress.")


def _require_catalog_paths(parser: argparse.ArgumentParser, args: argparse.Namespace) -> None:
    if args.catalog in {"ps1", "both"} and args.ps1_hats is None:
        parser.error("--ps1-hats is required with --catalog ps1 or both")
    if args.catalog in {"regalade", "both"} and args.regalade_hats is None:
        parser.error("--regalade-hats is required with --catalog regalade or both")


def _list_main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="Find hosts for every row in a position CSV.")
    parser.add_argument("--input", type=Path, required=True, help="CSV with ra and dec/declination columns.")
    parser.add_argument("--output", type=Path, default=Path("host_associations.csv"))
    _add_catalog_arguments(parser)
    args = parser.parse_args(argv)
    _require_catalog_paths(parser, args)
    try:
        associator = _associator(args)
        with args.input.open(newline="") as source:
            rows = list(csv.DictReader(source))
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    if not rows or "ra" not in rows[0] or ("dec" not in rows[0] and "declination" not in rows[0]):
        parser.error("--input must contain ra and dec or declination columns")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = ("name", "ra", "dec", "outcome", "host_id", "host_ra_deg", "host_dec_deg", "host_posterior_mean", "error")
    with args.output.open("w", newline="") as destination:
        writer = csv.DictWriter(destination, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            try:
                dec = row.get("dec") or row["declination"]
                redshift = float(row["redshift"]) if row.get("redshift") else None
                result = associator.find_host(float(row["ra"]), float(dec), redshift=redshift)
                best = result.host
                writer.writerow({"name": row.get("name"), "ra": row["ra"], "dec": dec, "outcome": result.outcome,
                                 "host_id": best.catalog_id if best else None, "host_ra_deg": best.ra_deg if best else None,
                                 "host_dec_deg": best.dec_deg if best else None,
                                 "host_posterior_mean": best.posterior_mean if best else None, "error": None})
            except (KeyError, TypeError, ValueError, OSError, RuntimeError) as exc:
                writer.writerow({"name": row.get("name"), "ra": row.get("ra"), "dec": row.get("dec", row.get("declination")),
                                 "outcome": "error", "host_id": None, "host_ra_deg": None, "host_dec_deg": None,
                                 "host_posterior_mean": None, "error": str(exc)})
    return 0


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--input" in argv:
        return _list_main(argv)

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ra", type=float, required=True, help="Right ascension in degrees.")
    parser.add_argument("--dec", type=float, required=True, help="Declination in degrees.")
    parser.add_argument("--position-error-arcsec", type=float)
    parser.add_argument("--redshift", type=float)
    parser.add_argument("--output", type=Path, help="Write JSON here; omit to print it.")
    _add_catalog_arguments(parser)
    args = parser.parse_args(argv)
    _require_catalog_paths(parser, args)
    try:
        result = _associator(args).find_host(
            args.ra, args.dec, position_error_arcsec=args.position_error_arcsec, redshift=args.redshift,
        )
    except (OSError, RuntimeError, ValueError) as exc:
        parser.error(str(exc))
    payload = result.model_dump_json(indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload)
    else:
        print(payload, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
