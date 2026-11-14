def greedy(student_ids, preferences, min_team_size, max_team_size, preference_limit):
    if not 1 <= min_team_size <= max_team_size:
        raise ValueError("Team sizes must satisfy 1 <= min_team_size <= max_team_size.")
    if preference_limit <= 0:
        raise ValueError("preference_limit must be positive.")

    student_ids = sorted(set(student_ids))
    if not student_ids:
        raise ValueError("At least one student is required.")

    student_count = len(student_ids)
    team_count = (student_count + max_team_size - 1) // max_team_size
    base_size, extra = divmod(student_count, team_count)
    if base_size < min_team_size:
        raise ValueError("The requested team sizes are impossible for these students.")
    target_sizes = [base_size + (index < extra) for index in range(team_count)]

    enrolled = set(student_ids)
    scores = {}
    for chooser_id, chosen_id, rank in preferences:
        if chooser_id not in enrolled or chosen_id not in enrolled:
            continue
        if not 1 <= rank <= preference_limit:
            continue
        pair = (chooser_id, chosen_id)
        scores[pair] = scores.get(pair, 0) + preference_limit - rank + 1

    teams = [[student_id] for student_id in student_ids[:team_count]]
    unassigned = set(student_ids[team_count:])
    while unassigned:
        for team, target_size in zip(teams, target_sizes):
            if len(team) >= target_size:
                continue
            student_id = max(
                unassigned,
                key=lambda candidate: (
                    sum(
                        scores.get((candidate, member), 0)
                        + scores.get((member, candidate), 0)
                        for member in team
                    ),
                    -candidate,
                ),
            )
            team.append(student_id)
            unassigned.remove(student_id)

    return teams
