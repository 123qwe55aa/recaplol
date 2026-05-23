# Player Version and Coach Design

## Goal

Add lightweight LoL client version visibility and an embedded AI Coach question box to the player page.

## Design

The player page shows a `LoLVersionCard` below the player summary. It fetches the latest Riot Data Dragon version at runtime from `https://ddragon.leagueoflegends.com/api/versions.json`, displays loading and failure states, and links users to Riot's official patch notes archive.

The player page also shows a `PlayerCoachChatPanel` below the version card. It reuses the existing `useCoachChat` hook and `/coach/players/{puuid}/chat` backend behavior, keeps messages in local page state, and links to `/coach/{puuid}` for report generation or deeper review.

## Scope

This change does not scrape patch note content, add a backend version endpoint, or auto-generate coach reports from the player page.
