# Database Plan

## Overview

This document describes the initial Supabase database design for the neighborhood threat monitoring MVP.

The design is centered on:

- `areas` for neighborhoods and monitored regions
- `events` for incident reports shown on the map
- `posts` and `post_comments` for the discussion feed
- user subscriptions and notification preferences
- media uploads for photo and video verification

## Privacy And GDPR Direction

The schema is intentionally privacy-first for user-submitted reports.

### Location Storage

- Do not store exact user-submitted source coordinates by default.
- Store incident geography as an approximate center plus radius.
- Render user-reported incidents as circles or fuzzy markers on the map.
- Use a location precision label to indicate whether the report is approximate to a building, street, block, or neighborhood.

### Reporter Coordinates

- Do not store `reported_from` for normal user reports in the MVP.
- If exact coordinates are ever required for trusted imported or admin data, model that separately from user-generated reports.

### Media Handling

- Support photo and video uploads as first-class records.
- Plan to strip EXIF metadata on upload.
- Include moderation and retention fields.
- Prefer private storage with signed URLs.

### Retention

- Add deletion and retention fields to user-generated content and media.
- Keep room for future anonymization workflows.

## Core Entities

### Profiles

Extends `auth.users` with application-facing account details and trust indicators.

Key fields:

- `id`
- `username`
- `display_name`
- `avatar_url`
- `karma`
- `trust_score`
- `streak_days`
- `badges`
- `deleted_at`

### Areas

Stores neighborhoods or monitored regions.

Key fields:

- `id`
- `name`
- `city`
- `country_code`
- `slug`
- `boundary`
- `center`
- `is_active`

### User Area Subscriptions

Lets a user monitor multiple neighborhoods.

Key fields:

- `user_id`
- `area_id`

### Notification Preferences

Stores per-user and per-area notification settings.

Key fields:

- `user_id`
- `area_id`
- `threat_types`
- `min_severity`
- `channels`
- `enabled`

### Events

Represents incidents that appear on the map and drive alerts.

Key fields:

- `id`
- `area_id`
- `reporter_id`
- `title`
- `description`
- `threat_type`
- `severity`
- `status`
- `occurred_at`
- `approx_center`
- `approx_radius_m`
- `location_precision`
- `location_label`
- `source_type`
- `source_url`
- `is_anonymous`
- `relevance_score`
- `verification_score`
- `comment_count`
- `contains_personal_data`
- `retention_until`
- `deleted_at`

### Event Media

Stores uploaded photo or video evidence tied to incidents.

Key fields:

- `id`
- `event_id`
- `uploader_id`
- `kind`
- `storage_path`
- `mime_type`
- `file_size_bytes`
- `width`
- `height`
- `duration_seconds`
- `captured_at`
- `is_primary`
- `moderation_status`
- `metadata_stripped`
- `contains_faces`
- `contains_license_plates`
- `retention_until`
- `deleted_at`

### Event Relevance Votes

Captures whether users consider an incident useful to others.

Key fields:

- `event_id`
- `user_id`
- `vote`

### Event Verification Votes

Captures whether users think a report is true, false, or still uncertain.

Key fields:

- `event_id`
- `user_id`
- `vote`

### Posts

Represents the discussion feed. Posts may optionally reference an incident.

Key fields:

- `id`
- `area_id`
- `author_id`
- `linked_event_id`
- `title`
- `body`
- `threat_type`
- `severity`
- `occurred_at`
- `score`
- `comment_count`
- `is_deleted`
- `deleted_at`

### Post Comments

Stores threaded discussion on posts.

Key fields:

- `id`
- `post_id`
- `author_id`
- `parent_comment_id`
- `body`
- `score`
- `is_deleted`
- `deleted_at`

### Notifications

Tracks outbound notifications to users.

Key fields:

- `id`
- `user_id`
- `event_id`
- `post_id`
- `channel`
- `payload`
- `sent_at`

## Proposed Enums

- `threat_type`
- `severity_level`
- `event_status`
- `relevance_vote`
- `verification_vote`
- `location_precision`
- `media_kind`
- `moderation_status`
- `notification_channel`

## Planned Supabase/Postgres Features

- PostGIS for neighborhood boundaries and approximate incident geography
- Supabase Auth plus `profiles`
- Supabase Storage for event media
- Row Level Security on user-generated tables
- Triggers for `updated_at`, counters, and trust/karma rollups

## MVP Notes

The minimum useful version should include:

- profiles
- areas
- user subscriptions
- notification preferences
- events
- event media
- relevance votes
- verification votes
- posts
- post comments
- notifications

## Open Questions

- Whether imported public incidents should be allowed to store more precise coordinates than user-submitted incidents.
- Whether verification votes should later distinguish trusted users from normal users.
- Whether media becomes visible immediately or only after moderation.
- Exact retention windows for incidents, media, and deleted account data.
