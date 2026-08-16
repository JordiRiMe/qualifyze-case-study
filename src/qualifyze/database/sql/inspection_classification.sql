WITH normalized_inspection_rows AS (
    /*
     * Normalize inspection rows and convert the classification
     * into an ordered severity.
     */
    SELECT
        inspection_id,
        btrim(fei_number::text) AS fei_number,
        inspection_end_date,
        NULLIF(btrim(state), '') AS state,
        NULLIF(btrim(product_type), '') AS product_type,
        project_area,

        CASE upper(btrim(classification_code))
            WHEN 'NAI' THEN 0
            WHEN 'VAI' THEN 1
            WHEN 'OAI' THEN 2
        END AS severity

    FROM public.inspections

    WHERE inspection_id IS NOT NULL
      AND fei_number IS NOT NULL
      AND country = 'United States'
      AND btrim(fei_number::text) <> ''
      AND inspection_end_date IS NOT NULL
      AND upper(btrim(classification_code))
            IN ('NAI', 'VAI', 'OAI')
),

inspection_events AS (
    /*
     * Collapse project-area rows into one physical inspection.
     * The worst project-area classification becomes the target.
     */
    SELECT
        inspection_id,
        fei_number,

        MAX(inspection_end_date)
            AS inspection_end_date,

        MAX(severity)
            AS severity,

        MAX(state)
            AS state,

        COUNT(*)::INTEGER
            AS source_row_count,

        COUNT(DISTINCT project_area)::INTEGER
            AS project_area_count

    FROM normalized_inspection_rows

    GROUP BY
        inspection_id,
        fei_number
),

labeled_inspections AS (
    SELECT
        inspection_id,
        fei_number,

        inspection_end_date AS prediction_date,

        state,
        severity,

        CASE severity
            WHEN 0 THEN 'NAI'
            WHEN 1 THEN 'VAI'
            WHEN 2 THEN 'OAI'
        END AS classification,

        severity > 0 AS adverse_classification,

        source_row_count,
        project_area_count

    FROM inspection_events
),

inspection_history AS (
    /*
     * Summarize all strictly earlier inspections and identify
     * the most recent one.
     */
    SELECT
        target.inspection_id,

        COUNT(previous.inspection_id)::INTEGER
            AS prior_inspection_count,

        MIN(previous.prediction_date)
            AS first_inspection_date,

        MAX(previous.prediction_date)
            AS previous_inspection_date,

        MAX(previous.severity)::INTEGER
            AS historical_worst_severity,

        (
            ARRAY_AGG(
                previous.inspection_id
                ORDER BY
                    previous.prediction_date DESC,
                    previous.inspection_id DESC
            ) FILTER (
                WHERE previous.inspection_id IS NOT NULL
            )
        )[1] AS previous_inspection_id,

        (
            ARRAY_AGG(
                previous.severity
                ORDER BY
                    previous.prediction_date DESC,
                    previous.inspection_id DESC
            ) FILTER (
                WHERE previous.inspection_id IS NOT NULL
            )
        )[1]::INTEGER AS previous_severity

    FROM labeled_inspections AS target

    LEFT JOIN labeled_inspections AS previous
        ON previous.fei_number = target.fei_number
       AND previous.prediction_date < target.prediction_date

    GROUP BY target.inspection_id
),

eligible_targets AS (
    /*
     * Restrict the cohort to inspections with at least one
     * observable previous inspection.
     */
    SELECT
        target.*,

        history.prior_inspection_count,
        history.first_inspection_date,
        history.previous_inspection_date,
        history.historical_worst_severity,
        history.previous_inspection_id,
        history.previous_severity

    FROM labeled_inspections AS target

    JOIN inspection_history AS history
        USING (inspection_id)
),

inspection_product_types AS (
    /*
     * Retain each distinct product type associated with a
     * physical inspection.
     */
    SELECT DISTINCT
        inspection_id,
        fei_number,
        product_type

    FROM normalized_inspection_rows

    WHERE product_type IS NOT NULL
),

product_history AS (
    /*
     * Only product types from earlier inspections are included.
     */
    SELECT
        target.inspection_id,

        COUNT(
            DISTINCT products.product_type
        )::INTEGER AS historical_product_type_count,

        MAX(
            CASE
                WHEN lower(products.product_type)
                    LIKE '%food%'
                THEN 1 ELSE 0
            END
        )::SMALLINT AS has_prior_product_food,

        MAX(
            CASE
                WHEN lower(products.product_type)
                    LIKE '%drug%'
                  OR lower(products.product_type)
                    LIKE '%pharma%'
                THEN 1 ELSE 0
            END
        )::SMALLINT AS has_prior_product_drug,

        MAX(
            CASE
                WHEN lower(products.product_type)
                    LIKE '%device%'
                THEN 1 ELSE 0
            END
        )::SMALLINT AS has_prior_product_device,

        MAX(
            CASE
                WHEN lower(products.product_type)
                    LIKE '%biologic%'
                  OR lower(products.product_type)
                    LIKE '%blood%'
                  OR lower(products.product_type)
                    LIKE '%tissue%'
                THEN 1 ELSE 0
            END
        )::SMALLINT AS has_prior_product_biologic,

        MAX(
            CASE
                WHEN lower(products.product_type)
                    LIKE '%veterinar%'
                  OR lower(products.product_type)
                    LIKE '%animal%'
                THEN 1 ELSE 0
            END
        )::SMALLINT AS has_prior_product_veterinary,

        MAX(
            CASE
                WHEN lower(products.product_type)
                    LIKE '%tobacco%'
                THEN 1 ELSE 0
            END
        )::SMALLINT AS has_prior_product_tobacco,

        MAX(
            CASE
                WHEN products.product_type IS NOT NULL
                 AND lower(products.product_type)
                        NOT LIKE '%food%'
                 AND lower(products.product_type)
                        NOT LIKE '%drug%'
                 AND lower(products.product_type)
                        NOT LIKE '%pharma%'
                 AND lower(products.product_type)
                        NOT LIKE '%device%'
                 AND lower(products.product_type)
                        NOT LIKE '%biologic%'
                 AND lower(products.product_type)
                        NOT LIKE '%blood%'
                 AND lower(products.product_type)
                        NOT LIKE '%tissue%'
                 AND lower(products.product_type)
                        NOT LIKE '%veterinar%'
                 AND lower(products.product_type)
                        NOT LIKE '%animal%'
                 AND lower(products.product_type)
                        NOT LIKE '%tobacco%'
                THEN 1 ELSE 0
            END
        )::SMALLINT AS has_prior_product_other

    FROM eligible_targets AS target

    LEFT JOIN labeled_inspections AS previous
        ON previous.fei_number = target.fei_number
       AND previous.prediction_date
            < target.prediction_date

    LEFT JOIN inspection_product_types AS products
        ON products.inspection_id
            = previous.inspection_id
       AND products.fei_number
            = previous.fei_number

    GROUP BY target.inspection_id
),

citation_history AS (
    /*
     * Citations are obtained only through earlier inspections.
     * Citations from the target inspection cannot enter.
     */
    SELECT
        target.inspection_id,

        COUNT(citation.id)::INTEGER
            AS prior_citation_count,

        COUNT(citation.id) FILTER (
            WHERE previous.inspection_id
                = target.previous_inspection_id
        )::INTEGER
            AS previous_inspection_citation_count,

        COUNT(
            DISTINCT citation.inspection_id
        )::INTEGER
            AS prior_inspections_with_citations

    FROM eligible_targets AS target

    LEFT JOIN labeled_inspections AS previous
        ON previous.fei_number = target.fei_number
       AND previous.prediction_date
            < target.prediction_date

    LEFT JOIN public.inspections_citations AS citation
        ON citation.inspection_id
            = previous.inspection_id

    GROUP BY target.inspection_id
),

cfr_history AS (
    /*
     * Count the number of earlier inspections in which each
     * normalized CFR provision appeared.
     */
    SELECT
        target.inspection_id,

        upper(
            btrim(citation.act_cfr_number)
        ) AS normalized_cfr,

        COUNT(
            DISTINCT citation.inspection_id
        )::INTEGER AS cited_inspection_count

    FROM eligible_targets AS target

    JOIN labeled_inspections AS previous
        ON previous.fei_number = target.fei_number
       AND previous.prediction_date
            < target.prediction_date

    JOIN public.inspections_citations AS citation
        ON citation.inspection_id
            = previous.inspection_id

    WHERE citation.act_cfr_number IS NOT NULL
      AND btrim(citation.act_cfr_number) <> ''

    GROUP BY
        target.inspection_id,
        upper(btrim(citation.act_cfr_number))
),

repeated_cfr_history AS (
    /*
     * A repeated CFR is one cited in at least two distinct
     * previous inspections.
     */
    SELECT
        inspection_id,

        COUNT(*) FILTER (
            WHERE cited_inspection_count >= 2
        )::INTEGER AS repeated_cfr_count

    FROM cfr_history

    GROUP BY inspection_id
),

published_483_history AS (
    /*
     * A Published 483 is included only if:
     * 1. its underlying record predates the target; and
     * 2. it was publicly published before the target.
     */
    SELECT
        target.inspection_id,

        COUNT(
            DISTINCT published.record_id
        )::INTEGER AS prior_published_483_count

    FROM eligible_targets AS target

    LEFT JOIN public.published483 AS published
        ON btrim(published.fei_number::text)
            = target.fei_number
       AND published.record_date
            < target.prediction_date
       AND published.publish_date
            < target.prediction_date

    GROUP BY target.inspection_id
),

compliance_action_events AS (
    /*
     * Deduplicate action-product rows into site-level actions.
     */
    SELECT DISTINCT
        btrim(fei_number::text) AS fei_number,
        action_taken_date,
        lower(btrim(action_type)) AS action_type,

        COALESCE(
            NULLIF(
                btrim(case_injunction_id::text),
                ''
            ),
            concat_ws(
                '|',
                btrim(fei_number::text),
                action_taken_date::text,
                lower(btrim(action_type))
            )
        ) AS action_key

    FROM public.compliance_actions

    WHERE fei_number IS NOT NULL
      AND btrim(fei_number::text) <> ''
      AND action_taken_date IS NOT NULL
),

warning_letter_history AS (
    SELECT
        target.inspection_id,

        COUNT(
            DISTINCT action.action_key
        ) FILTER (
            WHERE action.action_type
                LIKE '%warning%'
        )::INTEGER AS prior_warning_letter_count

    FROM eligible_targets AS target

    LEFT JOIN compliance_action_events AS action
        ON action.fei_number
            = target.fei_number
       AND action.action_taken_date
            < target.prediction_date

    GROUP BY target.inspection_id
),

recall_history AS (
    /*
     * event_id is counted rather than product rows because one
     * recall event can contain multiple products.
     */
    SELECT
        target.inspection_id,

        COUNT(
            DISTINCT recall.event_id
        )::INTEGER AS prior_recall_event_count

    FROM eligible_targets AS target

    LEFT JOIN public.recalls AS recall
        ON btrim(recall.fei_number::text)
            = target.fei_number
       AND recall.center_classification_date
            < target.prediction_date

    GROUP BY target.inspection_id
),

inserted AS (
    INSERT INTO features.inspection_classification_v1 (
        dataset_version,
        inspection_id,
        fei_number,
        prediction_date,
        target_classification,
        target_severity,
        target_adverse,
        prior_inspection_count,
        is_first_observed_inspection,
        days_since_previous_inspection,
        previous_classification_adverse,
        previous_classification_missing,
        historical_product_type_count,
        has_prior_product_food,
        has_prior_product_drug,
        has_prior_product_device,
        has_prior_product_biologic,
        has_prior_product_veterinary,
        has_prior_product_tobacco,
        has_prior_product_other,
        prior_citation_count,
        previous_inspection_citation_count,
        prior_citations_per_inspection,
        repeated_cfr_count,
        state,
        -- prior_published_483_count,
        prior_published_483_count_per_inspection,
        -- prior_warning_letter_count,
        prior_warning_letter_count_per_inspection,
        -- prior_recall_event_count
        prior_recall_event_count_per_inspection
    )
    SELECT
        :dataset_version,
        target.inspection_id,
        target.fei_number,
        target.prediction_date,

        /* Target variables */
        target.classification AS target_classification,
        target.severity AS target_severity,
        target.adverse_classification AS target_adverse,

        /* Inspection history */
        target.prior_inspection_count,
        CASE
            WHEN target.prior_inspection_count = 0 THEN 1
            ELSE 0
        END::SMALLINT AS is_first_observed_inspection,

        COALESCE(
            target.prediction_date - target.previous_inspection_date, 0
        ) AS days_since_previous_inspection,

        CASE
            WHEN target.previous_inspection_id IS NULL THEN 0
            WHEN target.previous_severity = 0 THEN 0
            WHEN target.previous_severity IN (1, 2) THEN 1
        END::SMALLINT AS previous_classification_adverse,
        
        CASE
            WHEN target.previous_inspection_id IS NULL THEN 1
            ELSE 0
        END::SMALLINT AS previous_classification_missing,

        /* Historical product types */
        COALESCE(
            product.historical_product_type_count,
            0
        ) AS historical_product_type_count,

        COALESCE(
            product.has_prior_product_food,
            0
        ) AS has_prior_product_food,

        COALESCE(
            product.has_prior_product_drug,
            0
        ) AS has_prior_product_drug,

        COALESCE(
            product.has_prior_product_device,
            0
        ) AS has_prior_product_device,

        COALESCE(
            product.has_prior_product_biologic,
            0
        ) AS has_prior_product_biologic,

        COALESCE(
            product.has_prior_product_veterinary,
            0
        ) AS has_prior_product_veterinary,

        COALESCE(
            product.has_prior_product_tobacco,
            0
        ) AS has_prior_product_tobacco,

        COALESCE(
            product.has_prior_product_other,
            0
        ) AS has_prior_product_other,

        /* Historical citations */
        COALESCE(
            citation.prior_citation_count,
            0
        ) AS prior_citation_count,

        COALESCE(
            citation.previous_inspection_citation_count,
            0
        ) AS previous_inspection_citation_count,

        CASE
            WHEN target.prior_inspection_count = 0 THEN 0.0
            ELSE
                COALESCE(
                citation.prior_citation_count,
                0
            )::DOUBLE PRECISION
            / target.prior_inspection_count
        END AS prior_citations_per_inspection,

        COALESCE(
            repeated_cfr.repeated_cfr_count,
            0
        ) AS repeated_cfr_count,

        /* Facility geography */
        target.state,

        /* Published Form 483 history */
        -- COALESCE(
        --     published_483.prior_published_483_count,
        --     0
        -- ) AS prior_published_483_count,

        CASE
            WHEN target.prior_inspection_count = 0 THEN 0.0
            ELSE
                COALESCE(
                    published_483.prior_published_483_count,
                    0
                )::DOUBLE PRECISION
                / target.prior_inspection_count
        END AS prior_published_483_count_per_inspection,

        /* Warning-letter history */
        -- COALESCE(
        --     warning.prior_warning_letter_count,
        --     0
        -- ) AS prior_warning_letter_count,

        CASE
            WHEN target.prior_inspection_count = 0 THEN 0.0
            ELSE
                COALESCE(
                    warning.prior_warning_letter_count,
                    0
                )::DOUBLE PRECISION
                / target.prior_inspection_count
        END AS prior_warning_letter_count_per_inspection,

        /* Recall history */
        -- COALESCE(
        --     recall.prior_recall_event_count,
        --     0
        -- ) AS prior_recall_count,

        CASE
            WHEN target.prior_inspection_count = 0
                THEN 0.0

            ELSE
                COALESCE(
                    recall.prior_recall_event_count,
                    0
                )::DOUBLE PRECISION
                / target.prior_inspection_count
        END AS prior_recall_event_count_per_inspection

    FROM eligible_targets AS target

    LEFT JOIN product_history AS product
        USING (inspection_id)

    LEFT JOIN citation_history AS citation
        USING (inspection_id)

    LEFT JOIN repeated_cfr_history AS repeated_cfr
        USING (inspection_id)

    LEFT JOIN published_483_history AS published_483
        USING (inspection_id)

    LEFT JOIN warning_letter_history AS warning
        USING (inspection_id)

    LEFT JOIN recall_history AS recall
        USING (inspection_id)
        
    RETURNING inspection_id
)

SELECT COUNT(*)::INTEGER AS inserted_count
FROM inserted;
