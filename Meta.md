```xml
<?xml version="1.0" encoding="UTF-8"?>
<databaseChangeLog
    xmlns="http://www.liquibase.org/xml/ns/dbchangelog"
    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
    xmlns:pro="http://www.liquibase.org/xml/ns/pro"
    xsi:schemaLocation="
      http://www.liquibase.org/xml/ns/dbchangelog
      https://www.liquibase.org/xml/ns/dbchangelog/dbchangelog-4.9.xsd
      http://www.liquibase.org/xml/ns/pro
      https://www.liquibase.org/xml/ns/pro/liquibase-pro-4.9.xsd">

  <!-- ================================================================= -->
  <!-- 1. Schema & table creation                                        -->
  <!-- ================================================================= -->
  <changeSet id="1-create-metadata-cache-core-schema" author="you">
    <!-- Enable UUID generation -->
    <preConditions onFail="MARK_RAN">
      <not>
        <extensionExists extensionName="pgcrypto"/>
      </not>
    </preConditions>
    <createExtension extensionName="pgcrypto" ifNotExists="true"/>

    <!-- Schemas -->
    <createSchema schemaName="core" ifNotExists="true"/>
    <createSchema schemaName="landing" ifNotExists="true"/>

    <!-- core.source -->
    <createTable schemaName="core" tableName="source">
      <column name="source_id" type="SERIAL">
        <constraints primaryKey="true" nullable="false"/>
      </column>
      <column name="source_name" type="TEXT">
        <constraints nullable="false" unique="true"/>
      </column>
      <column name="description" type="TEXT"/>
      <column name="created_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
      <column name="updated_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
    </createTable>

    <!-- core.entity_type -->
    <createTable schemaName="core" tableName="entity_type">
      <column name="entity_type_id" type="SERIAL">
        <constraints primaryKey="true" nullable="false"/>
      </column>
      <column name="source_id" type="INT">
        <constraints nullable="false"/>
      </column>
      <column name="name" type="TEXT">
        <constraints nullable="false"/>
      </column>
      <column name="description" type="TEXT"/>
      <column name="created_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
      <column name="updated_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
    </createTable>
    <addForeignKeyConstraint
        constraintName="fk_entity_type_source"
        baseSchemaName="core" baseTableName="entity_type" baseColumnNames="source_id"
        referencedSchemaName="core" referencedTableName="source" referencedColumnNames="source_id"
        onDelete="CASCADE"/>
    <addUniqueConstraint
        constraintName="uk_entity_type_source_name"
        schemaName="core" tableName="entity_type"
        columnNames="source_id,name"/>

    <!-- landing.raw_payload -->
    <createTable schemaName="landing" tableName="raw_payload">
      <column name="raw_id" type="BIGSERIAL">
        <constraints primaryKey="true" nullable="false"/>
      </column>
      <column name="source_id" type="INT">
        <constraints nullable="false"/>
      </column>
      <column name="endpoint" type="TEXT">
        <constraints nullable="false"/>
      </column>
      <column name="payload" type="JSONB">
        <constraints nullable="false"/>
      </column>
      <column name="fetched_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
      <column name="processed" type="BOOLEAN" defaultValueBoolean="false">
        <constraints nullable="false"/>
      </column>
    </createTable>
    <addForeignKeyConstraint
        constraintName="fk_raw_payload_source"
        baseSchemaName="landing" baseTableName="raw_payload" baseColumnNames="source_id"
        referencedSchemaName="core" referencedTableName="source" referencedColumnNames="source_id"
        onDelete="CASCADE"/>
    <createIndex indexName="idx_raw_payload_fetched_at"
                 schemaName="landing" tableName="raw_payload">
      <column name="fetched_at"/>
    </createIndex>

    <!-- core.entity -->
    <createTable schemaName="core" tableName="entity">
      <column name="entity_id" type="UUID" defaultValueComputed="gen_random_uuid()">
        <constraints primaryKey="true" nullable="false"/>
      </column>
      <column name="source_id" type="INT">
        <constraints nullable="false"/>
      </column>
      <column name="entity_type_id" type="INT">
        <constraints nullable="false"/>
      </column>
      <column name="external_key" type="TEXT">
        <constraints nullable="false"/>
      </column>
      <column name="name" type="TEXT"/>
      <column name="status" type="TEXT"/>
      <column name="last_seen" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
      <column name="fetched_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
      <column name="created_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
      <column name="updated_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
    </createTable>
    <addUniqueConstraint
        constraintName="uk_entity_source_extkey"
        schemaName="core" tableName="entity"
        columnNames="source_id,external_key"/>
    <addForeignKeyConstraint
        constraintName="fk_entity_source"
        baseSchemaName="core" baseTableName="entity" baseColumnNames="source_id"
        referencedSchemaName="core" referencedTableName="source" referencedColumnNames="source_id"
        onDelete="CASCADE"/>
    <addForeignKeyConstraint
        constraintName="fk_entity_entity_type"
        baseSchemaName="core" baseTableName="entity" baseColumnNames="entity_type_id"
        referencedSchemaName="core" referencedTableName="entity_type" referencedColumnNames="entity_type_id"
        onDelete="RESTRICT"/>
    <createIndex indexName="idx_entity_last_seen"
                 schemaName="core" tableName="entity">
      <column name="last_seen"/>
    </createIndex>
    <createIndex indexName="idx_entity_fetched_at"
                 schemaName="core" tableName="entity">
      <column name="fetched_at"/>
    </createIndex>

    <!-- core.entity_attribute -->
    <createTable schemaName="core" tableName="entity_attribute">
      <column name="entity_id" type="UUID">
        <constraints nullable="false"/>
      </column>
      <column name="attr_key" type="TEXT">
        <constraints nullable="false"/>
      </column>
      <column name="attr_value" type="TEXT"/>
      <column name="fetched_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
    </createTable>
    <addPrimaryKey
        constraintName="pk_entity_attribute"
        schemaName="core" tableName="entity_attribute"
        columnNames="entity_id,attr_key"/>
    <addForeignKeyConstraint
        constraintName="fk_entity_attribute_entity"
        baseSchemaName="core" baseTableName="entity_attribute" baseColumnNames="entity_id"
        referencedSchemaName="core" referencedTableName="entity" referencedColumnNames="entity_id"
        onDelete="CASCADE"/>
    <createIndex indexName="idx_attr_fetched_at"
                 schemaName="core" tableName="entity_attribute">
      <column name="fetched_at"/>
    </createIndex>

    <!-- core.entity_relation -->
    <createTable schemaName="core" tableName="entity_relation">
      <column name="relation_id" type="UUID" defaultValueComputed="gen_random_uuid()">
        <constraints primaryKey="true" nullable="false"/>
      </column>
      <column name="source_id" type="INT">
        <constraints nullable="false"/>
      </column>
      <column name="from_entity" type="UUID">
        <constraints nullable="false"/>
      </column>
      <column name="to_entity" type="UUID">
        <constraints nullable="false"/>
      </column>
      <column name="relation_type" type="TEXT">
        <constraints nullable="false"/>
      </column>
      <column name="fetched_at" type="TIMESTAMPTZ" defaultValueComputed="NOW()">
        <constraints nullable="false"/>
      </column>
    </createTable>
    <addForeignKeyConstraint
        constraintName="fk_rel_source"
        baseSchemaName="core" baseTableName="entity_relation" baseColumnNames="source_id"
        referencedSchemaName="core" referencedTableName="source" referencedColumnNames="source_id"
        onDelete="CASCADE"/>
    <addForeignKeyConstraint
        constraintName="fk_rel_from"
        baseSchemaName="core" baseTableName="entity_relation" baseColumnNames="from_entity"
        referencedSchemaName="core" referencedTableName="entity" referencedColumnNames="entity_id"
        onDelete="CASCADE"/>
    <addForeignKeyConstraint
        constraintName="fk_rel_to"
        baseSchemaName="core" baseTableName="entity_relation" baseColumnNames="to_entity"
        referencedSchemaName="core" referencedTableName="entity" referencedColumnNames="entity_id"
        onDelete="CASCADE"/>
    <createIndex indexName="idx_rel_fetched_at"
                 schemaName="core" tableName="entity_relation">
      <column name="fetched_at"/>
    </createIndex>
  </changeSet>

  <!-- ================================================================= -->
  <!-- 2. Seed sample data                                              -->
  <!-- ================================================================= -->
  <changeSet id="2-seed-sample-data" author="you">
    <loadData
        schemaName="core"
        tableName="source"
        file="db/changelog/data/source.csv"
        separator=","/>

    <loadData
        schemaName="core"
        tableName="entity_type"
        file="db/changelog/data/entity_type.csv"
        separator=","/>

    <loadData
        schemaName="landing"
        tableName="raw_payload"
        file="db/changelog/data/raw_payload.csv"
        separator=";"/>

    <loadData
        schemaName="core"
        tableName="entity"
        file="db/changelog/data/entity.csv"
        separator=","/>

    <loadData
        schemaName="core"
        tableName="entity_attribute"
        file="db/changelog/data/entity_attribute.csv"
        separator=","/>

    <loadData
        schemaName="core"
        tableName="entity_relation"
        file="db/changelog/data/entity_relation.csv"
        separator=","/>
  </changeSet>

</databaseChangeLog>

```

```sql
-- 1.1: separate by function: landing (raw), core (typed)
CREATE SCHEMA IF NOT EXISTS landing;
CREATE SCHEMA IF NOT EXISTS core;

-- 1.2: track each metadata source (so you can plug in Collibra, Atlas, …)
CREATE TABLE core.source (
  source_id      SERIAL      PRIMARY KEY,
  source_name    TEXT        NOT NULL UNIQUE,
  description    TEXT
);

-- 1.3: define the kinds of entities your system handles
CREATE TABLE core.entity_type (
  entity_type_id SERIAL      PRIMARY KEY,
  source_id      INT         NOT NULL REFERENCES core.source(source_id),
  name           TEXT        NOT NULL,
  UNIQUE (source_id, name)
);

-- 1.4: raw JSON landing area — a perfect place to debug
CREATE TABLE landing.raw_payload (
  raw_id         BIGSERIAL   PRIMARY KEY,
  source_id      INT         NOT NULL REFERENCES core.source(source_id),
  endpoint       TEXT        NOT NULL,            -- e.g. "/assets", "/types"
  payload        JSONB       NOT NULL,
  fetched_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed      BOOLEAN     NOT NULL DEFAULT FALSE
);

-- 1.5: core metadata entity table
CREATE TABLE core.entity (
  entity_id      UUID        PRIMARY KEY,
  source_id      INT         NOT NULL REFERENCES core.source(source_id),
  entity_type_id INT         NOT NULL REFERENCES core.entity_type(entity_type_id),
  external_key   TEXT        NOT NULL,            -- ID as given by the source
  name           TEXT,
  status         TEXT,
  last_seen      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  fetched_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  UNIQUE (source_id, external_key)
);

-- 1.6: key/value attributes per entity
CREATE TABLE core.entity_attribute (
  entity_id      UUID        NOT NULL REFERENCES core.entity(entity_id) ON DELETE CASCADE,
  attr_key       TEXT        NOT NULL,
  attr_value     TEXT,
  fetched_at     TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  PRIMARY KEY (entity_id, attr_key)
);

-- 1.7: relationships between entities (generic graph)
CREATE TABLE core.entity_relation (
  relation_id    UUID        PRIMARY KEY DEFAULT gen_random_uuid(),
  source_id      INT         NOT NULL REFERENCES core.source(source_id),
  from_entity    UUID        NOT NULL REFERENCES core.entity(entity_id),
  to_entity      UUID        NOT NULL REFERENCES core.entity(entity_id),
  relation_type  TEXT        NOT NULL,
  fetched_at     TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
```


```java
package com.example.metadata;

import com.fasterxml.jackson.databind.JsonNode;

/**
 * Strategy interface for pulling metadata from any source (Collibra, Atlas, etc.).
 * Defines one‐page fetch, raw‐JSON persistence, and merge/upsert into the core schema.
 */
public interface MetadataFetcher {

    /**
     * Fetch a single page of results.
     *
     * @param page zero‐based page index
     * @param size number of items per page
     * @return true if there are more pages to fetch after this one
     * @throws MetadataFetchException on network/auth failures
     */
    boolean fetchPage(int page, int size) throws MetadataFetchException;

    /**
     * Persist a raw JSON page into the landing.raw_payload table.
     *
     * @param page JsonNode representing the entire page payload
     * @throws MetadataPersistenceException on DB write errors
     */
    void persistRaw(JsonNode page) throws MetadataPersistenceException;

    /**
     * Merge any unprocessed landing rows into the core.entity, attribute, relation tables.
     * Should be idempotent: re‑running it won’t duplicate data.
     *
     * @throws MetadataPersistenceException on DB write errors
     */
    void upsertCore() throws MetadataPersistenceException;
}
```

```java
public class MetadataFetchException extends RuntimeException { /* ... */ }
public class MetadataPersistenceException extends RuntimeException { /* ... */ }
```
```java
package com.example.metadata.collibra;

import com.example.metadata.MetadataFetchException;
import com.example.metadata.MetadataPersistenceException;
import com.example.metadata.MetadataFetcher;
import com.example.metadata.collibra.client.AssetPage;
import com.example.metadata.collibra.client.CollibraApiClient;
import com.example.metadata.landing.RawPayloadEntity;
import com.example.metadata.landing.RawPayloadRepository;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import lombok.RequiredArgsConstructor;
import org.springframework.jdbc.core.JdbcTemplate;
import org.springframework.stereotype.Component;
import org.springframework.transaction.annotation.Transactional;

/**
 * Fetches metadata from Collibra via the REST API and caches it in Postgres.
 */
@Component
@RequiredArgsConstructor
public class CollibraRestStrategy implements MetadataFetcher {

    private final CollibraApiClient client;
    private final RawPayloadRepository rawRepo;
    private final JdbcTemplate jdbc;
    private final ObjectMapper mapper;

    private static final String ENDPOINT = "/assets";

    /**
     * Fetch one page of assets from Collibra.
     *
     * @param page zero‐based page index
     * @param size items per page
     * @return true if more pages remain
     */
    @Override
    public boolean fetchPage(int page, int size) throws MetadataFetchException {
        try {
            AssetPage assetPage = client.getAssets()
                                        .getAssets(page, size);  // auto‐generated client call
            // Persist raw JSON for this page
            persistRaw(mapper.valueToTree(assetPage));
            // Continue if Collibra reports more pages
            return assetPage.getTotalPages() > page + 1;
        } catch (Exception e) {
            throw new MetadataFetchException(
                "Failed to fetch page " + page + " from Collibra", e);
        }
    }

    /**
     * Save the raw API response into landing.raw_payload.
     */
    @Override
    public void persistRaw(JsonNode page) throws MetadataPersistenceException {
        try {
            RawPayloadEntity entity = RawPayloadEntity.builder()
                .sourceId(client.getConfig().getSourceId())  // your config bean
                .endpoint(ENDPOINT)
                .payload(page)
                .build();
            rawRepo.save(entity);
        } catch (Exception e) {
            throw new MetadataPersistenceException("Error persisting raw payload", e);
        }
    }

    /**
     * Merge from landing.raw_payload → core.entity, core.entity_attribute, core.entity_relation.
     * Marks rows processed to avoid re‐processing.
     */
    @Transactional
    @Override
    public void upsertCore() throws MetadataPersistenceException {
        try {
            // Upsert assets into core.entity
            jdbc.update("""
                INSERT INTO core.entity (entity_id, source_id, entity_type_id,
                                         external_key, name, status, last_seen, fetched_at)
                SELECT gen_random_uuid(),
                       rp.source_id,
                       et.entity_type_id,
                       elem->>'id',
                       elem->>'name',
                       elem->>'status',
                       (elem->>'lastModifiedAt')::timestamptz,
                       NOW()
                  FROM landing.raw_payload rp
                  JOIN jsonb_array_elements(
                         rp.payload->'results'
                     ) AS elem ON rp.endpoint = ?
                  JOIN core.entity_type et
                    ON et.source_id = rp.source_id
                   AND et.name = elem->'type'->>'name'
                 WHERE rp.processed = FALSE
                ON CONFLICT (source_id, external_key) DO UPDATE
                  SET name       = EXCLUDED.name,
                      status     = EXCLUDED.status,
                      last_seen  = EXCLUDED.last_seen,
                      fetched_at = EXCLUDED.fetched_at;
                """, ENDPOINT);

            // Upsert attributes
            jdbc.update("""
                INSERT INTO core.entity_attribute (entity_id, attr_key, attr_value, fetched_at)
                SELECT e.entity_id,
                       attr->>'key',
                       attr->>'value',
                       NOW()
                  FROM landing.raw_payload rp
                  JOIN jsonb_array_elements(rp.payload->'results') AS elem
                  JOIN jsonb_each(elem->'attributes')      AS attr
                  JOIN core.entity e
                    ON e.source_id    = rp.source_id
                   AND e.external_key = elem->>'id'
                 WHERE rp.processed = FALSE
                ON CONFLICT (entity_id, attr_key) DO UPDATE
                  SET attr_value = EXCLUDED.attr_value,
                      fetched_at = EXCLUDED.fetched_at;
                """);

            // Upsert relations (if any)
            jdbc.update("""
                INSERT INTO core.entity_relation (relation_id, source_id,
                                                  from_entity, to_entity,
                                                  relation_type, fetched_at)
                SELECT gen_random_uuid(),
                       rp.source_id,
                       e_from.entity_id,
                       e_to.entity_id,
                       rel->>'type',
                       NOW()
                  FROM landing.raw_payload rp
                  JOIN jsonb_array_elements(rp.payload->'results') AS elem
                  JOIN jsonb_array_elements(elem->'relations') AS rel
                  JOIN core.entity e_from
                    ON e_from.source_id    = rp.source_id
                   AND e_from.external_key = elem->>'id'
                  JOIN core.entity e_to
                    ON e_to.source_id      = rp.source_id
                   AND e_to.external_key   = rel->>'targetId'
                 WHERE rp.processed = FALSE
                ON CONFLICT (relation_id) DO NOTHING;
                """);

            // Mark payload rows as processed
            jdbc.update("""
                UPDATE landing.raw_payload
                   SET processed = TRUE
                 WHERE endpoint = ?
                   AND processed = FALSE
                """, ENDPOINT);

        } catch (Exception e) {
            throw new MetadataPersistenceException("Error upserting core tables", e);
        }
    }
}

```
```java
package com.example.metadata.landing;

import com.fasterxml.jackson.databind.JsonNode;
import com.vladmihalcea.hibernate.type.json.JsonBinaryType;
import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.Type;
import org.hibernate.annotations.TypeDef;
import org.hibernate.annotations.TypeDefs;

import java.time.Instant;

/**
 * JPA entity for landing.raw_payload
 */
@Entity
@Table(schema = "landing", name = "raw_payload")
@TypeDefs({
    @TypeDef(name = "jsonb", typeClass = JsonBinaryType.class)
})
@Data
@Builder
@NoArgsConstructor
@AllArgsConstructor
public class RawPayloadEntity {

    /** Primary key (BIGSERIAL) */
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "raw_id", updatable = false, nullable = false)
    private Long rawId;

    /** FK to core.source.source_id */
    @Column(name = "source_id", nullable = false)
    private Integer sourceId;

    /** The API endpoint (e.g. "/assets") */
    @Column(name = "endpoint", nullable = false)
    private String endpoint;

    /** Raw JSON payload (JSONB) */
    @Type(type = "jsonb")
    @Column(name = "payload", columnDefinition = "jsonb", nullable = false)
    private JsonNode payload;

    /** When we fetched this page */
    @Column(name = "fetched_at", nullable = false, updatable = false,
            columnDefinition = "TIMESTAMPTZ DEFAULT NOW()")
    private Instant fetchedAt;

    /** Has this page been processed into core.* tables? */
    @Column(name = "processed", nullable = false)
    private Boolean processed;
}
```
```java
public interface RawPayloadRepository
  extends JpaRepository<RawPayloadEntity, Long> { }
```

```java
package com.example.metadata.collibra.config;

import com.example.metadata.collibra.client.ApiClient;
import com.example.metadata.collibra.client.CollibraApiClient;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;
import org.springframework.web.reactive.function.client.WebClient;

/**
 * Configures the CollibraApiClient generated from the OpenAPI spec.
 */
@Configuration
public class CollibraClientConfig {

    @Value("${collibra.base-url}")
    private String baseUrl;

    @Value("${collibra.username}")
    private String username;

    @Value("${collibra.password}")
    private String password;

    /**
     * Shared WebClient with basic auth for Collibra.
     */
    @Bean
    public WebClient collibraWebClient() {
        return WebClient.builder()
            .baseUrl(baseUrl)
            .defaultHeaders(headers ->
                headers.setBasicAuth(username, password))
            .build();
    }

    /**
     * OpenAPI‑generated ApiClient, wired to use our WebClient.
     */
    @Bean
    public ApiClient apiClient(WebClient collibraWebClient) {
        return new ApiClient()
            .setBasePath(baseUrl)
            .setWebClient(collibraWebClient);
    }

    /**
     * Convenience CollibraApiClient that groups all endpoints.
     */
    @Bean
    public CollibraApiClient collibraApiClient(ApiClient apiClient) {
        return new CollibraApiClient(apiClient);
    }
}
```

```yaml
collibra:
  base-url: https://my‑tenant.us.cloud.collibra.com
  username: your‑user
  password: your‑pass
```

```java
package com.example.metadata.batch;

import com.example.metadata.MetadataFetcher;
import lombok.RequiredArgsConstructor;
import org.springframework.batch.core.*;
import org.springframework.batch.core.configuration.annotation.*;
import org.springframework.batch.repeat.RepeatStatus;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

/**
 * Defines a Batch job with:
 * 1) fetchStep: pages through Collibra assets and persists raw JSON
 * 2) mergeStep: merges landing.raw_payload → core tables
 */
@Configuration
@EnableBatchProcessing
@RequiredArgsConstructor
public class BatchConfig {

    private final JobBuilderFactory    jobBuilderFactory;
    private final StepBuilderFactory   stepBuilderFactory;
    private final MetadataFetcher      metadataFetcher;

    private static final int PAGE_SIZE = 500;

    @Bean
    public Job metadataJob(JobCompletionNotificationListener listener,
                           Step fetchStep,
                           Step mergeStep) {
        return jobBuilderFactory.get("metadataJob")
            .listener(listener)
            .start(fetchStep)
            .next(mergeStep)
            .build();
    }

    @Bean
    public Step fetchStep() {
        return stepBuilderFactory.get("fetchStep")
            .tasklet((contribution, chunkContext) -> {
                int page = 0;
                boolean hasMore;
                do {
                    hasMore = metadataFetcher.fetchPage(page++, PAGE_SIZE);
                } while (hasMore);
                return RepeatStatus.FINISHED;
            })
            .build();
    }

    @Bean
    public Step mergeStep() {
        return stepBuilderFactory.get("mergeStep")
            .tasklet((contribution, chunkContext) -> {
                metadataFetcher.upsertCore();
                return RepeatStatus.FINISHED;
            })
            .build();
    }

    @Bean
    public JobCompletionNotificationListener listener() {
        return new JobCompletionNotificationListener();
    }
}
```

```java
package com.example.metadata.batch;

import lombok.extern.slf4j.Slf4j;
import org.springframework.batch.core.*;
import org.springframework.stereotype.Component;

/**
 * Simple listener to log job start/end.
 */
@Component
@Slf4j
public class JobCompletionNotificationListener implements JobExecutionListener {

    @Override
    public void beforeJob(JobExecution jobExecution) {
        log.info(">>> Starting job: {}", jobExecution.getJobInstance().getJobName());
    }

    @Override
    public void afterJob(JobExecution jobExecution) {
        if (jobExecution.getStatus() == BatchStatus.COMPLETED) {
            log.info(">>> Job completed successfully");
        } else {
            log.warn(">>> Job finished with status: {}", jobExecution.getStatus());
        }
    }
}

```


