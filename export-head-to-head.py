"""Export regular-season scores from the Dynasty Plebs head-to-head archive."""

import argparse
import json
from decimal import Decimal
from pathlib import Path


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("archive", type=Path)
args = parser.parse_args()
archive = json.loads(args.archive.read_text(encoding="utf-8"))
assert archive["league"] == "Dynasty Plebs"

managers = {key: value["name"] for key, value in archive["managers"].items()}
seasons = {}
for year, season in sorted(archive["seasons"].items()):
    coverage = season["coverage"]["regularSeason"]
    games = []
    for game in sorted(season["matchups"], key=lambda game: (game["week"], game["id"])):
        if game["phase"] != "regular-season":
            continue
        a, b = game["managerA"], game["managerB"]
        assert a != b and a in managers and b in managers
        scores = [Decimal(str(game[f"score{side}"])) * 100 for side in "AB"]
        assert all(score == int(score) for score in scores)
        games.append([game["week"], a, b, *map(int, scores)])
    assert len(games) == coverage["gamesImported"], year
    seasons[year] = {
        "complete": coverage["status"] == "complete",
        "expected": coverage["gamesExpected"],
        "games": games,
    }

output = {"managers": managers, "seasons": seasons}
Path(__file__).with_name("head-to-head-data.json").write_text(
    json.dumps(output, separators=(",", ":")) + "\n", encoding="utf-8"
)
