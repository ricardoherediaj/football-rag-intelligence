#!/usr/bin/env python3
"""
Inspect match data from MinIO to understand structure for chunking strategy.
"""

from minio import Minio
import json
import sys


def inspect_whoscored_data():
    """Inspect WhoScored data structure."""
    client = Minio(
        'localhost:9000',
        access_key='minioadmin',
        secret_key='minioadmin',
        secure=False
    )

    print("=" * 80)
    print("WHOSCORED DATA INSPECTION")
    print("=" * 80)

    # List objects
    objects = list(client.list_objects('football-data', prefix='whoscored/', recursive=True))
    print(f"\nTotal WhoScored matches: {len(objects)}")

    if objects:
        # Get first match
        obj = objects[0]
        print(f"\nSample file: {obj.object_name}")

        data = client.get_object('football-data', obj.object_name)
        content = json.loads(data.read())

        print(f"\nTop-level keys: {list(content.keys())}")

        # Match info
        if 'matchInfo' in content:
            match_info = content['matchInfo']
            print(f"\nMatch Info keys: {list(match_info.keys())}")
            print(f"  Home Team: {match_info.get('homeTeam', {}).get('name')}")
            print(f"  Away Team: {match_info.get('awayTeam', {}).get('name')}")
            print(f"  Score: {match_info.get('score')}")
            print(f"  Date: {match_info.get('startDate')}")

        # Events
        if 'events' in content:
            events = content['events']
            print(f"\nTotal events: {len(events)}")
            if events:
                print(f"\nSample event (first):")
                print(json.dumps(events[0], indent=2)[:500])

                # Count event types
                event_types = {}
                for event in events:
                    event_type = event.get('type', {}).get('displayName', 'Unknown')
                    event_types[event_type] = event_types.get(event_type, 0) + 1

                print(f"\nEvent type distribution:")
                for event_type, count in sorted(event_types.items(), key=lambda x: x[1], reverse=True)[:10]:
                    print(f"  {event_type}: {count}")

        # Players
        if 'playerIdNameDictionary' in content:
            players = content['playerIdNameDictionary']
            print(f"\nTotal players: {len(players)}")
            print(f"Sample players: {list(players.values())[:5]}")


def inspect_fotmob_data():
    """Inspect Fotmob data structure."""
    client = Minio(
        'localhost:9000',
        access_key='minioadmin',
        secret_key='minioadmin',
        secure=False
    )

    print("\n\n")
    print("=" * 80)
    print("FOTMOB DATA INSPECTION")
    print("=" * 80)

    # List objects
    objects = list(client.list_objects('football-data', prefix='fotmob/', recursive=True))
    print(f"\nTotal Fotmob shot files: {len(objects)}")

    if objects:
        # Get first match
        obj = objects[0]
        print(f"\nSample file: {obj.object_name}")

        data = client.get_object('football-data', obj.object_name)
        content = json.loads(data.read())

        print(f"\nTop-level keys: {list(content.keys())}")

        if 'shotmap' in content:
            shotmap = content['shotmap']
            print(f"\nShotmap keys: {list(shotmap.keys())}")

            if 'shots' in shotmap:
                shots = shotmap['shots']
                print(f"\nTotal shots: {len(shots)}")
                if shots:
                    print(f"\nSample shot (first):")
                    print(json.dumps(shots[0], indent=2))


def main():
    try:
        inspect_whoscored_data()
        inspect_fotmob_data()
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
