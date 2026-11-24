from app.models import ViralBenchmark


def register_and_login(client, test_db, *, phone, role="artist", verified=False):
    registered = client.post(
        "/auth/register",
        json={
            "name": f"{role.title()} account",
            "phone": phone,
            "pin": "1234",
            "role": role,
            "city": "Douala",
        },
    )
    assert registered.status_code == 201
    if verified:
        with test_db() as db:
            from app.models import User

            user = db.scalars(
                __import__("sqlalchemy").select(User).where(User.phone == "+237" + phone)
            ).first()
            user.verified = True
            db.add(user)
            db.commit()
    login = client.post(
        "/auth/login",
        json={"phone": phone, "pin": "1234"},
    )
    assert login.status_code == 200
    return login.json()["access_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def create_benchmark(test_db, user_phone):
    with test_db() as db:
        from app.models import User

        user = db.scalars(
            __import__("sqlalchemy").select(User).where(
                User.phone == "+237" + user_phone
            )
        ).first()
        benchmark = ViralBenchmark(
            user_id=user.id,
            title="Viral benchmark",
            genre="makossa",
            broadcast_stations_count=10,
            viral_reach_notes="Regional",
            audio_filename="benchmark.wav",
            musical_key="C",
            key_index=0,
            tempo_bpm=112,
            flow_density=4,
            power_score=70,
            rms_energy=0.28,
            brightness_hz=2400,
            hook_timestamp_sec=8,
        )
        db.add(benchmark)
        db.commit()
        db.refresh(benchmark)
        return benchmark.id


def test_release_snapshot_dashboard_and_acknowledge(client, test_db):
    artist_token = register_and_login(client, test_db, phone="690123461")
    benchmark_id = create_benchmark(test_db, "690123461")

    released = client.post(
        "/releases",
        headers=auth(artist_token),
        json={"title": "After Dark", "benchmark_id": benchmark_id},
    )
    assert released.status_code == 201
    release_id = released.json()["id"]

    first = client.post(
        f"/canary/crawl/{release_id}",
        headers=auth(artist_token),
        json={
            "week_number": 1,
            "weekly_streams": 120000,
            "radio_tv_spins": 18,
            "early_skip_rate_pct": 19,
            "social_mentions": 70,
            "top_city": "Douala",
        },
    )
    assert first.status_code == 201

    second = client.post(
        f"/canary/crawl/{release_id}",
        headers=auth(artist_token),
        json={
            "week_number": 2,
            "weekly_streams": 68000,
            "radio_tv_spins": 25,
            "early_skip_rate_pct": 43,
            "social_mentions": 165,
            "top_city": "Douala",
        },
    )
    assert second.status_code == 201
    categories = {item["category"] for item in second.json()["insights"]}
    assert "MOMENTUM_DECAY" in categories
    assert "HOOK_DROP_OFF" in categories
    assert "REGIONAL_SURGE" in categories

    duplicate = client.post(
        f"/canary/crawl/{release_id}",
        headers=auth(artist_token),
        json={
            "week_number": 2,
            "weekly_streams": 1,
            "radio_tv_spins": 1,
            "early_skip_rate_pct": 1,
            "social_mentions": 1,
            "top_city": "Douala",
        },
    )
    assert duplicate.status_code == 409

    dashboard = client.get("/advisor/dashboard", headers=auth(artist_token))
    assert dashboard.status_code == 200
    assert dashboard.json()["weekly_momentum_status"] == "momentum_decay"
    assert len(dashboard.json()["trajectory"]) == 2
    insight_id = dashboard.json()["insights"][0]["id"]

    acknowledged = client.post(
        f"/advisor/insights/{insight_id}/acknowledge",
        headers=auth(artist_token),
    )
    assert acknowledged.status_code == 200
    assert acknowledged.json()["acknowledged"] is True


def test_verified_broadcaster_can_log_airplay(client, test_db):
    artist_token = register_and_login(client, test_db, phone="690123462")
    benchmark_id = create_benchmark(test_db, "690123462")
    released = client.post(
        "/releases",
        headers=auth(artist_token),
        json={"title": "Radio single", "benchmark_id": benchmark_id},
    )
    release_id = released.json()["id"]

    broadcaster_token = register_and_login(
        client, test_db, phone="690123463", role="broadcaster", verified=True
    )
    logged = client.post(
        f"/releases/{release_id}/airplay",
        headers=auth(broadcaster_token),
        json={"city": "Douala", "outlet_name": "Canary FM", "spins_count": 12},
    )
    assert logged.status_code == 201
    assert logged.json()["spins_count"] == 12

    fan_token = register_and_login(client, test_db, phone="690123464", role="fan")
    forbidden = client.post(
        f"/releases/{release_id}/airplay",
        headers=auth(fan_token),
        json={"city": "Douala", "outlet_name": "Fan station", "spins_count": 5},
    )
    assert forbidden.status_code == 403
