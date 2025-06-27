## Technical Document: Generic Metadata Ingestion and Caching Approach

### 1\. Introduction

This document outlines a robust and generic approach for ingesting and caching metadata from external sources (e.g., Collibra, Apache Atlas) into a centralized PostgreSQL database. The core idea is to maintain a "landing zone" for raw data and a "core" schema for structured, typed, and normalized metadata. This layered approach ensures data integrity, facilitates debugging, and supports incremental updates and historical tracking of metadata changes.

### 2\. Architectural Overview

The system design leverages Spring Boot for application development, Spring Batch for orchestrating ingestion jobs, Liquibase for database schema management, and JPA/Hibernate for object-relational mapping. A key abstraction is the `MetadataFetcher` interface, which allows for pluggable implementations for different metadata sources.

**Diagram: High-Level Architecture**

```
+-------------------+        +---------------------+        +---------------------+
| External Metadata |        | Metadata Ingestion  |        |  PostgreSQL Database|
| Source (e.g.,     | <----->| Application         | <----->|                     |
| Collibra, Atlas)  |        | (Spring Boot, Batch)|        |  +----------------+ |
+-------------------+        +---------------------+        |  | landing schema | |
                                   |                        |  +----------------+ |
                                   |                        |  | core schema    | |
                                   |                        |  +----------------+ |
                                   |                        +---------------------+
                                   |
                                   | (Database Migrations)
                                   v
                             +-------------+
                             |  Liquibase  |
                             +-------------+
```

### 3\. Database Schema Design

The database schema is designed with two primary schemas: `landing` and `core`. This separation is crucial for the ingestion process.

  * **`landing` Schema**: Stores raw, unprocessed JSON payloads fetched directly from external metadata sources. This acts as a staging area and a valuable debugging resource.
  * **`core` Schema**: Contains normalized and structured metadata, including entities, attributes, and relationships, providing a unified view of all ingested metadata.

#### 3.1. `core` Schema Tables

The `core` schema is designed to be source-agnostic and flexible, capable of representing various types of metadata.

  * **`core.source`**: Tracks each external metadata source (e.g., Collibra, Atlas).

      * `source_id` (SERIAL, PK)
      * `source_name` (TEXT, UNIQUE)
      * `description` (TEXT)

  * **`core.entity_type`**: Defines the different types of entities (e.g., `Table`, `Column`, `Report`) handled by the system for a given source.

      * `entity_type_id` (SERIAL, PK)
      * `source_id` (INT, FK to `core.source`)
      * `name` (TEXT)
      * `description` (TEXT)
      * Unique constraint on `(source_id, name)`

  * **`core.entity`**: The central table for all metadata entities. Each entity is uniquely identified and linked to its source and type.

      * `entity_id` (UUID, PK, default `gen_random_uuid()`)
      * `source_id` (INT, FK to `core.source`)
      * `entity_type_id` (INT, FK to `core.entity_type`)
      * `external_key` (TEXT, ID from the source system)
      * `name` (TEXT)
      * `status` (TEXT)
      * `last_seen` (TIMESTAMPTZ, last time seen in source, default NOW())
      * `fetched_at` (TIMESTAMPTZ, when ingested, default NOW())
      * Unique constraint on `(source_id, external_key)`

  * **`core.entity_attribute`**: Stores key-value attributes for each entity, providing flexibility for diverse metadata properties.

      * `entity_id` (UUID, PK, FK to `core.entity`, `ON DELETE CASCADE`)
      * `attr_key` (TEXT, PK)
      * `attr_value` (TEXT)
      * `fetched_at` (TIMESTAMPTZ, default NOW())
      * Primary key on `(entity_id, attr_key)`

  * **`core.entity_relation`**: Represents relationships between entities, forming a generic graph structure.

      * `relation_id` (UUID, PK, default `gen_random_uuid()`)
      * `source_id` (INT, FK to `core.source`)
      * `from_entity` (UUID, FK to `core.entity`, `ON DELETE CASCADE`)
      * `to_entity` (UUID, FK to `core.entity`, `ON DELETE CASCADE`)
      * `relation_type` (TEXT)
      * `fetched_at` (TIMESTAMPTZ, default NOW())

#### 3.2. `landing` Schema Tables

  * **`landing.raw_payload`**: Stores the verbatim JSON response received from the external metadata API.
      * `raw_id` (BIGSERIAL, PK)
      * `source_id` (INT, FK to `core.source`)
      * `endpoint` (TEXT, e.g., "/assets")
      * `payload` (JSONB, the raw JSON)
      * `fetched_at` (TIMESTAMPTZ, default NOW())
      * `processed` (BOOLEAN, default `FALSE`, indicates if moved to `core`)

**Diagram: Database Schema (Simplified ERD)**

```
+-------------------+  1---+---* +----------------+     1---+---* +----------+
| core.source       |     |   | core.entity_type |           |   | core.entity|
+-------------------+         |   +----------------+           |   +----------+
| source_id (PK)    | <-+-----+-> | entity_type_id (PK)  |       |   | entity_id (PK) |
| source_name       |    |   | source_id (FK)       |       +-->| source_id (FK) |
| description       |    |   | name                 |           | entity_type_id (FK)
+-------------------+    |   | description          |           | external_key   |
                         |   +----------------+           |   | name           |
                         |                                |   | status         |
                         |                                |   | last_seen      |
                         |                                |   | fetched_at     |
                         |                                +---+----------------+
                         |
                         | 1
                         |
+---------------------+  |
| landing.raw_payload |  |
+---------------------+  |
| raw_id (PK)         |  |
| source_id (FK) <----+--+
| endpoint            |
| payload (JSONB)     |
| fetched_at          |
| processed           |
+---------------------+

+---------------------+     *---+---1 +------------------+
| core.entity         |           |   | core.entity_attribute|
+---------------------+           |   +------------------+
| entity_id (PK) <----+-----------+-> | entity_id (PK, FK) |
| ...                 |               | attr_key (PK)    |
+---------------------+               | attr_value       |
                                      | fetched_at       |
                                      +------------------+

+---------------------+     *---+---1 +------------------+
| core.entity         |           |   | core.entity_relation |
+---------------------+           |   +------------------+
| entity_id (PK) <----+-----------+-> | relation_id (PK) |
| ...                 | from_entity   | source_id (FK)   |
+---------------------+           |   | from_entity (FK) |
                                  |   | to_entity (FK)   |
                                  |   | relation_type    |
                                  |   | fetched_at       |
                                  +---+------------------+
                                  to_entity
```

### 4\. Metadata Ingestion Process

The ingestion process is orchestrated by Spring Batch and consists of two main steps: `fetchStep` and `mergeStep`.

#### 4.1. `MetadataFetcher` Interface

The `MetadataFetcher` interface is the core abstraction for integrating with different metadata sources. It defines three key operations:

  * **`fetchPage(int page, int size)`**: Fetches a single page of metadata from the external source.
  * **`persistRaw(JsonNode page)`**: Persists the raw JSON payload of the fetched page into the `landing.raw_payload` table.
  * **`upsertCore()`**: Merges unprocessed raw payloads from the `landing` schema into the `core` schema, performing upserts (insert or update) to ensure idempotency.

#### 4.2. `CollibraRestStrategy` Implementation

An example implementation for Collibra is provided by `CollibraRestStrategy`.

  * **`fetchPage`**: Uses an auto-generated Collibra API client to retrieve assets page by page. The raw `AssetPage` JSON is then passed to `persistRaw`.
  * **`persistRaw`**: Creates a `RawPayloadEntity` from the `JsonNode` and saves it using `RawPayloadRepository` into `landing.raw_payload`.
  * **`upsertCore`**: This crucial step can be implemented in two ways:
      * **JDBC-based Upsert (Direct SQL)**: Uses `JdbcTemplate` to execute direct SQL `INSERT ... ON CONFLICT DO UPDATE` statements. This approach offers high performance and fine-grained control over the upsert logic for `core.entity`, `core.entity_attribute`, and `core.entity_relation`. After successful upsert, it marks the processed `raw_payload` rows as `processed = TRUE`.
      * **JPA/Hibernate-based Upsert (Declarative)**: Delegates the upsert logic to a `JpaCoreUpsertService`. This service iterates through unprocessed raw payloads, maps JSON elements to JPA entities (`CoreEntity`, `CoreAttribute`, `CoreRelation`), and uses Spring Data JPA repositories (`CoreEntityRepository`, `CoreAttributeRepository`, `CoreRelationRepository`) to persist them. It handles checking for existing entities by `source_id` and `external_key` and either updates them or creates new ones.

**Diagram: Metadata Ingestion Flow**

```
+-------------------+     +---------------------+     +--------------------------+
| External Metadata |     | MetadataFetcher     |     | PostgreSQL Database      |
| Source (e.g.,     |     | (e.g., CollibraRestStrategy) | +----------------------+ |
| Collibra API)     |     |                     |     | | landing.raw_payload  | |
+-------------------+     +---------------------+     | +----------------------+ |
          |                     |   fetchPage(page, size)         |                  |
          | (REST API Calls)    +-------------------+             |                  |
          |-------------------->| Client API Call   |             |                  |
          |                     | (e.g., getAssets) |             |                  |
          |                     +-------------------+             |                  |
          |                             | persistRaw(JsonNode)    |                  |
          |<----------------------------|-------------------------+                  |
          | Raw JSON Response           |                         |                  |
          |                             | Save to raw_payload     |                  |
          |                             V                         |                  |
          |                     +-------------------+             |                  |
          |                     | RawPayloadRepository|             |                  |
          |                     +-------------------+             |                  |
          |                                                       |                  |
          |                     +-------------------+             |                  |
          |                     |   upsertCore()    |             |                  |
          |                     |---------------------------------| Raw Payload (Unprocessed)
          |                     V                                 |
          |             +-----------------------------------------+                  |
          |             | Transform & Upsert (SQL or JPA)         |                  |
          |             | (Reads from landing.raw_payload,        |                  |
          |             | writes/updates core.entity,             |                  |
          |             | core.entity_attribute,                  |                  |
          |             | core.entity_relation)                   |                  |
          |             +-----------------------------------------+                  |
          |                                                       | +----------------+
          |                                                       | | core.entity    |
          |                                                       | | core.attributes|
          |                                                       | | core.relations |
          |                                                       | +----------------+
          |                                                       |                  |
          |             +-------------------+                     |                  |
          |             | Mark Processed    |<--------------------+                  |
          |             | (raw_payload.processed = TRUE)          |                  |
          |             +-------------------+                     |                  |
          |                                                       +------------------+
```

#### 4.3. Spring Batch Configuration

The `BatchConfig` class sets up a Spring Batch job named `metadataJob` with two steps:

  * **`fetchStep`**: This step iteratively calls `metadataFetcher.fetchPage()` until all pages of metadata are fetched and persisted as raw JSON.
  * **`mergeStep`**: This step calls `metadataFetcher.upsertCore()` to process all unprocessed raw payloads from the `landing` schema into the `core` schema.

### 5\. Technologies Used

  * **Spring Boot**: Provides the foundational framework for building the application.
  * **Spring Batch**: Facilitates robust, scalable, and fault-tolerant batch processing for metadata ingestion.
  * **Spring Data JPA / Hibernate**: Used for ORM capabilities, primarily for managing `RawPayloadEntity` and optionally for core upserts.
  * **PostgreSQL**: The chosen relational database, leveraging features like JSONB for raw payloads and UUIDs for entity IDs.
  * **Liquibase**: Manages database schema changes and ensures version control of the database structure.
  * **Jackson**: For JSON processing, especially for handling `JsonNode` payloads.
  * **Project Lombok**: Reduces boilerplate code for Java beans.
  * **WebClient (Spring WebFlux)**: For making non-blocking HTTP requests to external metadata APIs.

### 6\. Configuration

Application properties are managed via `application.yaml` (or `application.properties`). Essential configurations include:

  * **Collibra API details**: `base-url`, `username`, `password` for connecting to the Collibra instance.
  * **Database connection details**: Standard Spring Boot data source properties (not explicitly shown in the provided `Meta.md` but implied by Liquibase and Spring Data JPA usage).

### 7\. Benefits of the Approach

  * **Idempotency**: The `upsertCore` logic ensures that re-running the process does not duplicate data, as it either inserts new records or updates existing ones based on unique keys (`source_id`, `external_key` for `core.entity`; `entity_id`, `attr_key` for `core.entity_attribute`).
  * **Auditability & Debugging**: Storing raw payloads in the `landing` schema provides a historical record of all fetched data, which is invaluable for debugging and auditing. The `processed` flag ensures that data is processed only once.
  * **Flexibility**: The `MetadataFetcher` interface allows for easy integration of new metadata sources by implementing the interface.
  * **Performance**: The JDBC-based `upsertCore` offers high performance for bulk data operations by leveraging database-native upsert capabilities. The JPA-based approach, while potentially less performant for very large datasets due to row-by-row processing, offers more declarative development.
  * **Scalability**: Spring Batch is designed for scalable batch processing, making it suitable for handling large volumes of metadata.
  * **Schema Evolution**: Liquibase ensures that database schema changes are managed in a controlled and versioned manner.

### 8\. Future Enhancements

  * **Delta Processing**: Implement logic to fetch only changed metadata from sources that support it, reducing load and processing time.
  * **Error Handling and Retry Mechanisms**: Enhance error handling within the batch process for specific failure scenarios and introduce retry logic.
  * **Historical Tracking**: Implement soft deletes or versioning within the `core` tables to maintain a full history of metadata changes, not just the `last_seen` timestamp.
  * **Concurrency**: Explore concurrent processing of raw payloads in `upsertCore` for further performance gains, especially with the JPA approach.
  * **More Generic Relationships**: The current `entity_relation` table is generic; consider extending it with relation attributes or different relation types if needed.
