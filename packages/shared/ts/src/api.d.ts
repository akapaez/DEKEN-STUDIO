/**
 * GENERADO desde la API (FastAPI → OpenAPI). No editar a mano.
 * Regenerar: pnpm generate:api
 */

export interface paths {
    "/api/v1/audit": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Audit Events */
        get: operations["list_audit_events"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/login": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Login */
        post: operations["login"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/logout": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Logout */
        post: operations["logout"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/me": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Me */
        get: operations["me"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/auth/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Change Password */
        post: operations["change_password"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/brand/assets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Brand Assets */
        get: operations["list_brand_assets"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/brand/assets/{asset_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Brand Asset */
        get: operations["get_brand_asset"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Brand Asset */
        patch: operations["update_brand_asset"];
        trace?: never;
    };
    "/api/v1/brand/assets/{asset_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Brand Asset */
        post: operations["archive_brand_asset"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/brand/assets/{asset_id}/download-url": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Brand Download Url */
        get: operations["brand_download_url"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/brand/uploads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start Brand Upload */
        post: operations["start_brand_upload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/brand/uploads/{asset_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete Brand Upload */
        post: operations["complete_brand_upload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/files/{object_id}/download-url": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Download Url
         * @description URL firmada de corta duración. Solo para ficheros verificados.
         */
        get: operations["download_url"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health/live": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Live
         * @description El proceso responde. No comprueba dependencias.
         */
        get: operations["live"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/health/ready": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /**
         * Ready
         * @description Disponibilidad. 503 si fallan BD o almacenamiento; `degraded` si solo falla Redis.
         */
        get: operations["ready"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jobs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Jobs */
        get: operations["list_jobs"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jobs/{job_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Job */
        get: operations["get_job"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jobs/{job_id}/cancel": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancel Job */
        post: operations["cancel_job"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/jobs/{job_id}/retry": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Retry Job */
        post: operations["retry_job"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/assets": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Media Assets */
        get: operations["list_media_assets"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/assets/{asset_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Get Media Asset */
        get: operations["get_media_asset"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update Media Asset */
        patch: operations["update_media_asset"];
        trace?: never;
    };
    "/api/v1/media/assets/{asset_id}/archive": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Archive Media Asset */
        post: operations["archive_media_asset"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/assets/{asset_id}/original-url": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Original Url */
        get: operations["media_original_url"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/assets/{asset_id}/rights": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        /** Update Media Rights */
        put: operations["update_media_rights"];
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/assets/{asset_id}/waveform": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Media Waveform */
        get: operations["media_waveform"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/tags": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Media Tags */
        get: operations["list_media_tags"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/uploads": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Start Media Upload */
        post: operations["start_media_upload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/uploads/{asset_id}/abort": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Abort Media Upload */
        post: operations["abort_media_upload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/uploads/{asset_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete Media Upload */
        post: operations["complete_media_upload"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/media/uploads/{asset_id}/parts": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Media Upload Parts */
        post: operations["media_upload_parts"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/renders/engine": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** Render Engine */
        get: operations["render_engine"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/renders/evaluation": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Create Evaluation Render
         * @description Encola la composición de evaluación técnica (5 s, 1080×1920, 30 fps).
         */
        post: operations["create_evaluation_render"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/renders/timeline": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Create Timeline Render */
        post: operations["create_timeline_render"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/selftest": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /**
         * Render Selftest
         * @description Encola un autotest de render con señal SINTÉTICA (no es contenido de DEKEN).
         */
        post: operations["render_selftest"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/system/status": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** System Status */
        get: operations["system_status"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Users */
        get: operations["list_users"];
        put?: never;
        /** Create User */
        post: operations["create_user"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/{user_id}": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        /** Update User */
        patch: operations["update_user"];
        trace?: never;
    };
    "/api/v1/users/{user_id}/password": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Reset Password */
        post: operations["reset_password"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/users/roles": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Roles */
        get: operations["list_roles"];
        put?: never;
        post?: never;
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/worker/heartbeat": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Heartbeat */
        post: operations["heartbeat"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/worker/jobs/{job_id}/cancelled": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Cancelled */
        post: operations["cancelled"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/worker/jobs/{job_id}/complete": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Complete */
        post: operations["complete"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/worker/jobs/{job_id}/fail": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Fail */
        post: operations["fail"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/worker/jobs/{job_id}/outputs": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Request Output */
        post: operations["request_output"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/worker/jobs/{job_id}/progress": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Progress */
        post: operations["progress"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/worker/jobs/claim": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Claim */
        post: operations["claim"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/workers": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        /** List Workers */
        get: operations["list_workers"];
        put?: never;
        /** Register Worker */
        post: operations["register_worker"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
    "/api/v1/workers/{worker_id}/revoke": {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        get?: never;
        put?: never;
        /** Revoke Worker */
        post: operations["revoke_worker"];
        delete?: never;
        options?: never;
        head?: never;
        patch?: never;
        trace?: never;
    };
}
export type webhooks = Record<string, never>;
export interface components {
    schemas: {
        /** AiStatus */
        AiStatus: {
            /** Configured */
            configured: boolean;
            /** Provider */
            provider: string | null;
        };
        /** AuditEventOut */
        AuditEventOut: {
            /** Action */
            action: string;
            /** Actor Id */
            actor_id: string | null;
            /** Actor Label */
            actor_label: string | null;
            /** Actor Type */
            actor_type: string;
            /** Details */
            details: {
                [key: string]: unknown;
            };
            /** Id */
            id: number;
            /** Ip */
            ip: string | null;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
            /** Outcome */
            outcome: string;
            /** Request Id */
            request_id: string | null;
            /** Target Id */
            target_id: string | null;
            /** Target Type */
            target_type: string | null;
        };
        /** AuditListOut */
        AuditListOut: {
            /** Items */
            items: components["schemas"]["AuditEventOut"][];
            /** Next Before */
            next_before: number | null;
        };
        /** BrandAssetOut */
        BrandAssetOut: {
            /** Analysis */
            analysis: {
                [key: string]: unknown;
            } | null;
            /** Aspect Ratio */
            aspect_ratio: number | null;
            /** Color Mismatch */
            color_mismatch: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Declared Color */
            declared_color: string | null;
            /** Family */
            family: string | null;
            /** Font Family */
            font_family: string | null;
            /** Font Style */
            font_style: string | null;
            /** Font Weight */
            font_weight: number | null;
            /** Has Alpha */
            has_alpha: boolean | null;
            /** Height */
            height: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "logo" | "font" | "image";
            /** License Ref */
            license_ref: string | null;
            /** Measured Color Hex */
            measured_color_hex: string | null;
            /** Measured Color Name */
            measured_color_name: string | null;
            /** Name */
            name: string;
            /** Notes */
            notes: string | null;
            /** Original Filename */
            original_filename: string;
            /** Preview Url */
            preview_url: string | null;
            /** Recommended Background */
            recommended_background: ("dark" | "light" | "any") | null;
            /** Status */
            status: string;
            /** Status Reason */
            status_reason: string | null;
            /** Usage Background */
            usage_background: ("dark" | "light" | "any") | null;
            /** Width */
            width: number | null;
        };
        /** BrandUpdateRequest */
        BrandUpdateRequest: {
            /** Declared Color */
            declared_color?: string | null;
            /** Family */
            family?: string | null;
            /** License Ref */
            license_ref?: string | null;
            /** Name */
            name?: string | null;
            /** Notes */
            notes?: string | null;
            /** Usage Background */
            usage_background?: ("dark" | "light" | "any") | null;
        };
        /** BrandUploadOut */
        BrandUploadOut: {
            /**
             * Asset Id
             * Format: uuid
             */
            asset_id: string;
            /** Headers */
            headers: {
                [key: string]: string;
            };
            /** Upload Url */
            upload_url: string;
        };
        /** BrandUploadRequest */
        BrandUploadRequest: {
            /** Declared Color */
            declared_color?: string | null;
            /** Family */
            family?: string | null;
            /** Filename */
            filename: string;
            /**
             * Kind
             * @enum {string}
             */
            kind: "logo" | "font" | "image";
            /** License Ref */
            license_ref?: string | null;
            /** Name */
            name: string;
            /** Size Bytes */
            size_bytes: number;
        };
        /** CheckOut */
        CheckOut: {
            /** Bucket */
            bucket?: string | null;
            /** Error */
            error?: string | null;
            /** Latency Ms */
            latency_ms?: number | null;
            /** Migration */
            migration?: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "error";
        };
        /** ClaimedJob */
        ClaimedJob: {
            /** Attempt */
            attempt: number;
            /**
             * Contract Version
             * @default 1
             */
            contract_version: number;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Inputs */
            inputs: components["schemas"]["JobInput"][];
            /**
             * Lease Expires At
             * Format: date-time
             */
            lease_expires_at: string;
            /** Lease Seconds */
            lease_seconds: number;
            /** Max Attempts */
            max_attempts: number;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Queue */
            queue: string;
            /** Timeout S */
            timeout_s: number;
            /** Type */
            type: string;
        };
        /** ClaimRequest */
        ClaimRequest: {
            /** Job Types */
            job_types: string[];
            /** Queues */
            queues: components["schemas"]["Queue"][];
            /**
             * Wait Seconds
             * @default 20
             */
            wait_seconds: number;
        };
        /** CompleteRequest */
        CompleteRequest: {
            /** Outputs */
            outputs: components["schemas"]["OutputDeclaration"][];
            /** Result */
            result?: {
                [key: string]: unknown;
            };
        };
        /** DownloadUrlOut */
        DownloadUrlOut: {
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Filename */
            filename: string;
            /** Url */
            url: string;
        };
        /** FailRequest */
        FailRequest: {
            /** Code */
            code: string;
            /** Details */
            details?: {
                [key: string]: unknown;
            } | null;
            /** Message */
            message: string;
            /**
             * Retryable
             * @default false
             */
            retryable: boolean;
        };
        /** FfprobeStatus */
        FfprobeStatus: {
            /** Available */
            available: boolean;
            /** Version */
            version: string | null;
        };
        /** HealthOut */
        HealthOut: {
            /** Checks */
            checks: {
                [key: string]: "ok" | "error";
            };
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "degraded" | "error";
        };
        /** HTTPValidationError */
        HTTPValidationError: {
            /** Detail */
            detail?: components["schemas"]["ValidationError"][];
        };
        /** JobDetailOut */
        JobDetailOut: {
            /** Events */
            events: components["schemas"]["JobEventOut"][];
            job: components["schemas"]["JobOut"];
            /** Outputs */
            outputs: components["schemas"]["JobOutputOut"][];
        };
        /** JobEventOut */
        JobEventOut: {
            /** Attempt */
            attempt: number;
            /** Data */
            data: {
                [key: string]: unknown;
            };
            /** Id */
            id: number;
            /** Kind */
            kind: string;
            /** Message */
            message: string | null;
            /**
             * Occurred At
             * Format: date-time
             */
            occurred_at: string;
        };
        /** JobInput */
        JobInput: {
            /** Content Type */
            content_type: string;
            /** Duration S */
            duration_s?: number | null;
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Extension */
            extension?: string | null;
            /** Has Audio */
            has_audio?: boolean | null;
            /** Height */
            height?: number | null;
            /** Key */
            key?: string | null;
            /** Kind */
            kind?: string | null;
            /** Name */
            name: string;
            /**
             * Object Id
             * Format: uuid
             */
            object_id: string;
            /** Sha256 */
            sha256: string | null;
            /** Size Bytes */
            size_bytes: number | null;
            /** Url */
            url: string;
            /** Width */
            width?: number | null;
        };
        /** JobListOut */
        JobListOut: {
            /** Items */
            items: components["schemas"]["JobOut"][];
            /** Next Before */
            next_before: string | null;
        };
        /** JobOut */
        JobOut: {
            /** Attempts */
            attempts: number;
            /** Cancel Requested */
            cancel_requested: boolean;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Error */
            error: {
                [key: string]: unknown;
            } | null;
            /** Finished At */
            finished_at: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Lease Owner Id */
            lease_owner_id: string | null;
            /** Max Attempts */
            max_attempts: number;
            /** Payload */
            payload: {
                [key: string]: unknown;
            };
            /** Priority */
            priority: number;
            /** Progress */
            progress: number;
            /** Progress Message */
            progress_message: string | null;
            /** Queue */
            queue: string;
            /** Result */
            result: {
                [key: string]: unknown;
            } | null;
            /**
             * Run After
             * Format: date-time
             */
            run_after: string;
            /** Started At */
            started_at: string | null;
            status: components["schemas"]["JobStatus"];
            /** Type */
            type: string;
            /**
             * Updated At
             * Format: date-time
             */
            updated_at: string;
        };
        /** JobOutputOut */
        JobOutputOut: {
            /** Attempt */
            attempt: number;
            /** Kind */
            kind: string;
            /** Name */
            name: string;
            stored_object: components["schemas"]["StoredObjectOut"];
            /** Verification */
            verification: {
                [key: string]: unknown;
            } | null;
            /** Verified */
            verified: boolean;
        };
        /** JobsStatus */
        JobsStatus: {
            /** By Status */
            by_status: {
                [key: string]: number;
            };
            /** Failed Last 24H */
            failed_last_24h: number;
        };
        /**
         * JobStatus
         * @enum {string}
         */
        JobStatus: "queued" | "processing" | "completed" | "failed" | "cancelled";
        /** JobTransitionAck */
        JobTransitionAck: {
            /**
             * Id
             * Format: uuid
             */
            id: string;
            status: components["schemas"]["JobStatus"];
        };
        /** LeaseAck */
        LeaseAck: {
            /** Cancel Requested */
            cancel_requested: boolean;
            /**
             * Lease Expires At
             * Format: date-time
             */
            lease_expires_at: string;
        };
        /** LoginRequest */
        LoginRequest: {
            /** Email */
            email: string;
            /** Password */
            password: string;
        };
        /** MediaAssetDetailOut */
        MediaAssetDetailOut: {
            /** Archived At */
            archived_at: string | null;
            /** Audio Codec */
            audio_codec: string | null;
            /** Consent Reference */
            consent_reference: string | null;
            /**
             * Consent Status
             * @enum {string}
             */
            consent_status: "not_required" | "pending" | "granted" | "denied";
            /** Container */
            container: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Declared Size Bytes */
            declared_size_bytes: number;
            /** Derivatives */
            derivatives: {
                [key: string]: components["schemas"]["StoredObjectOut"];
            };
            /** Description */
            description: string | null;
            /** Duplicate Of Id */
            duplicate_of_id: string | null;
            /** Duration S */
            duration_s: number | null;
            /**
             * Dynamic Range
             * @description HDR de origen (hlg/pq): póster, tira y proxy se convierten a SDR BT.709
             */
            dynamic_range?: ("sdr" | "hlg" | "pq") | null;
            /** Fps */
            fps: number | null;
            /** Has Audio */
            has_audio: boolean | null;
            /** Has Waveform */
            has_waveform: boolean;
            /** Height */
            height: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Ingest Job Id */
            ingest_job_id: string | null;
            /** Location */
            location: string | null;
            /** Orientation */
            orientation: string | null;
            /** Original Filename */
            original_filename: string;
            original_object: components["schemas"]["StoredObjectOut"] | null;
            /**
             * People Present
             * @enum {string}
             */
            people_present: "yes" | "no" | "unknown";
            /** Poster Url */
            poster_url: string | null;
            /** Probe */
            probe: {
                [key: string]: unknown;
            } | null;
            /** Proxy Url */
            proxy_url: string | null;
            /** Recorded At */
            recorded_at: string | null;
            /** Rights Owner */
            rights_owner: string;
            /** Rights Updated At */
            rights_updated_at: string | null;
            /** Rotation */
            rotation: number | null;
            /** Sha256 */
            sha256: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "uploading" | "processing" | "ready" | "rejected" | "failed" | "duplicate" | "cancelled";
            /** Status Reason */
            status_reason: string | null;
            /** Strip Frames */
            strip_frames: number | null;
            /** Strip Url */
            strip_url: string | null;
            /** Tags */
            tags: string[];
            /** Title */
            title: string;
            /** Usable For Production */
            usable_for_production: boolean;
            /** Usage Restrictions */
            usage_restrictions: string | null;
            /** Video Codec */
            video_codec: string | null;
            /** Width */
            width: number | null;
        };
        /** MediaAssetOut */
        MediaAssetOut: {
            /** Archived At */
            archived_at: string | null;
            /** Audio Codec */
            audio_codec: string | null;
            /** Consent Reference */
            consent_reference: string | null;
            /**
             * Consent Status
             * @enum {string}
             */
            consent_status: "not_required" | "pending" | "granted" | "denied";
            /** Container */
            container: string | null;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Declared Size Bytes */
            declared_size_bytes: number;
            /** Description */
            description: string | null;
            /** Duplicate Of Id */
            duplicate_of_id: string | null;
            /** Duration S */
            duration_s: number | null;
            /**
             * Dynamic Range
             * @description HDR de origen (hlg/pq): póster, tira y proxy se convierten a SDR BT.709
             */
            dynamic_range?: ("sdr" | "hlg" | "pq") | null;
            /** Fps */
            fps: number | null;
            /** Has Audio */
            has_audio: boolean | null;
            /** Height */
            height: number | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Ingest Job Id */
            ingest_job_id: string | null;
            /** Location */
            location: string | null;
            /** Orientation */
            orientation: string | null;
            /** Original Filename */
            original_filename: string;
            /**
             * People Present
             * @enum {string}
             */
            people_present: "yes" | "no" | "unknown";
            /** Poster Url */
            poster_url: string | null;
            /** Recorded At */
            recorded_at: string | null;
            /** Rights Owner */
            rights_owner: string;
            /** Rights Updated At */
            rights_updated_at: string | null;
            /** Rotation */
            rotation: number | null;
            /** Sha256 */
            sha256: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "uploading" | "processing" | "ready" | "rejected" | "failed" | "duplicate" | "cancelled";
            /** Status Reason */
            status_reason: string | null;
            /** Strip Frames */
            strip_frames: number | null;
            /** Strip Url */
            strip_url: string | null;
            /** Tags */
            tags: string[];
            /** Title */
            title: string;
            /** Usable For Production */
            usable_for_production: boolean;
            /** Usage Restrictions */
            usage_restrictions: string | null;
            /** Video Codec */
            video_codec: string | null;
            /** Width */
            width: number | null;
        };
        /** MediaListOut */
        MediaListOut: {
            /** Items */
            items: components["schemas"]["MediaAssetOut"][];
            /** Total */
            total: number;
        };
        /** MediaRightsRequest */
        MediaRightsRequest: {
            /** Consent Reference */
            consent_reference?: string | null;
            /** Consent Status */
            consent_status?: ("not_required" | "pending" | "granted" | "denied") | null;
            /** People Present */
            people_present?: ("yes" | "no" | "unknown") | null;
            /** Rights Owner */
            rights_owner?: string | null;
            /** Usage Restrictions */
            usage_restrictions?: string | null;
        };
        /** MediaUpdateRequest */
        MediaUpdateRequest: {
            /** Description */
            description?: string | null;
            /** Location */
            location?: string | null;
            /** Recorded At */
            recorded_at?: string | null;
            /** Tags */
            tags?: string[] | null;
            /** Title */
            title?: string | null;
        };
        /** MediaUploadOut */
        MediaUploadOut: {
            /**
             * Asset Id
             * Format: uuid
             */
            asset_id: string;
            /** Max Parts Per Request */
            max_parts_per_request: number;
            /** Part Count */
            part_count: number;
            /** Part Size Bytes */
            part_size_bytes: number;
        };
        /** MediaUploadRequest */
        MediaUploadRequest: {
            /**
             * Content Type
             * @default
             */
            content_type: string;
            /** Filename */
            filename: string;
            /** Size Bytes */
            size_bytes: number;
            /** Title */
            title?: string | null;
        };
        /** MeOut */
        MeOut: {
            /** Csrf Token */
            csrf_token: string;
            /** Permissions */
            permissions: components["schemas"]["Permission"][];
            /**
             * Session Expires At
             * Format: date-time
             */
            session_expires_at: string;
            user: components["schemas"]["UserOut"];
        };
        /** OutputDeclaration */
        OutputDeclaration: {
            /** Name */
            name: string;
            /**
             * Object Id
             * Format: uuid
             */
            object_id: string;
            /** Sha256 */
            sha256: string;
            /** Size Bytes */
            size_bytes: number;
        };
        /** OutputUploadRequest */
        OutputUploadRequest: {
            /** Content Type */
            content_type: string;
            /** Name */
            name: string;
            /** Size Bytes */
            size_bytes: number;
        };
        /** OutputUploadTicket */
        OutputUploadTicket: {
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
            /** Headers */
            headers: {
                [key: string]: string;
            };
            /**
             * Method
             * @default PUT
             */
            method: string;
            /**
             * Object Id
             * Format: uuid
             */
            object_id: string;
            /** Upload Url */
            upload_url: string;
        };
        /** PartUrlOut */
        PartUrlOut: {
            /** Part Number */
            part_number: number;
            /** Url */
            url: string;
        };
        /** PartUrlsRequest */
        PartUrlsRequest: {
            /** Part Numbers */
            part_numbers: number[];
        };
        /** PasswordChangeRequest */
        PasswordChangeRequest: {
            /** Current Password */
            current_password: string;
            /** New Password */
            new_password: string;
        };
        /**
         * Permission
         * @enum {string}
         */
        Permission: "system:read" | "system:manage" | "users:manage" | "workers:manage" | "audit:read" | "jobs:read" | "jobs:manage" | "files:read" | "media:read" | "media:write" | "media:rights" | "brand:read" | "brand:manage" | "render:create";
        /** ProgressReport */
        ProgressReport: {
            /** Message */
            message?: string | null;
            /** Progress */
            progress: number;
        };
        /**
         * Queue
         * @enum {string}
         */
        Queue: "render" | "analysis";
        /** RemotionEvalRequest */
        RemotionEvalRequest: {
            /**
             * Subtitle
             * @default Motor de composición
             */
            subtitle: string;
            /**
             * Title
             * @default DEKEN STUDIO AI
             */
            title: string;
        };
        /** RemotionStatus */
        RemotionStatus: {
            /** Commercial Renders Enabled */
            commercial_renders_enabled: boolean;
            /**
             * License Mode
             * @enum {string}
             */
            license_mode: "evaluation" | "company";
        };
        /** RenderEngineOut */
        RenderEngineOut: {
            /** Commercial Renders Enabled */
            commercial_renders_enabled: boolean;
            /**
             * Engine
             * @constant
             */
            engine: "remotion";
            /**
             * License Mode
             * @enum {string}
             */
            license_mode: "evaluation" | "company";
            /** Note */
            note: string;
            /** Workers With Remotion */
            workers_with_remotion: string[];
        };
        /**
         * Role
         * @enum {string}
         */
        Role: "admin" | "editor" | "reviewer" | "viewer";
        /** RoleInfo */
        RoleInfo: {
            /** Label */
            label: string;
            /** Permissions */
            permissions: components["schemas"]["Permission"][];
            role: components["schemas"]["Role"];
        };
        /** SelftestRequest */
        SelftestRequest: {
            /**
             * Duration S
             * @default 3
             */
            duration_s: number;
        };
        /** StoredObjectOut */
        StoredObjectOut: {
            /** Content Type */
            content_type: string;
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Kind */
            kind: string;
            /** Media Info */
            media_info: {
                [key: string]: unknown;
            } | null;
            /** Sha256 */
            sha256: string | null;
            /** Size Bytes */
            size_bytes: number | null;
            /** Status */
            status: string;
            /** Verified At */
            verified_at: string | null;
        };
        /** SystemStatusOut */
        SystemStatusOut: {
            ai: components["schemas"]["AiStatus"];
            /** Checks */
            checks: {
                [key: string]: components["schemas"]["CheckOut"];
            };
            /** Environment */
            environment: string;
            ffprobe: components["schemas"]["FfprobeStatus"];
            jobs: components["schemas"]["JobsStatus"];
            remotion: components["schemas"]["RemotionStatus"];
            /**
             * Server Time
             * Format: date-time
             */
            server_time: string;
            /**
             * Status
             * @enum {string}
             */
            status: "ok" | "degraded" | "error";
            /** Version */
            version: string;
            workers: components["schemas"]["WorkersStatus"];
        };
        /** TagCountOut */
        TagCountOut: {
            /** Count */
            count: number;
            /** Tag */
            tag: string;
        };
        /** TimelineRenderRequest */
        TimelineRenderRequest: {
            /**
             * Purpose
             * @default evaluation
             * @enum {string}
             */
            purpose: "evaluation" | "production";
            /** Timeline */
            timeline: {
                [key: string]: unknown;
            };
            /** Title */
            title?: string | null;
        };
        /** UserCreateRequest */
        UserCreateRequest: {
            /** Email */
            email: string;
            /** Full Name */
            full_name: string;
            /** Password */
            password: string;
            role: components["schemas"]["Role"];
        };
        /** UserOut */
        UserOut: {
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Email */
            email: string;
            /** Full Name */
            full_name: string;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Is Active */
            is_active: boolean;
            /** Last Login At */
            last_login_at: string | null;
            role: components["schemas"]["Role"];
        };
        /** UserPasswordResetRequest */
        UserPasswordResetRequest: {
            /** Password */
            password: string;
        };
        /** UserUpdateRequest */
        UserUpdateRequest: {
            /** Full Name */
            full_name?: string | null;
            /** Is Active */
            is_active?: boolean | null;
            role?: components["schemas"]["Role"] | null;
        };
        /** ValidationError */
        ValidationError: {
            /** Context */
            ctx?: Record<string, never>;
            /** Input */
            input?: unknown;
            /** Location */
            loc: (string | number)[];
            /** Message */
            msg: string;
            /** Error Type */
            type: string;
        };
        /** WaveformOut */
        WaveformOut: {
            /** Duration S */
            duration_s: number;
            /** Peaks */
            peaks: number[];
            /** Version */
            version: number;
        };
        /** WorkerCapabilities */
        WorkerCapabilities: {
            /** Encoders */
            encoders?: string[];
            /** Engines */
            engines?: {
                [key: string]: string;
            };
            /** Ffmpeg Version */
            ffmpeg_version?: string | null;
            /** Ffprobe Version */
            ffprobe_version?: string | null;
            /** Hwaccels */
            hwaccels?: string[];
            /** Job Types */
            job_types?: string[];
            /**
             * Max Concurrency
             * @default 1
             */
            max_concurrency: number;
        };
        /** WorkerCreatedOut */
        WorkerCreatedOut: {
            /**
             * Token
             * @description Se muestra una sola vez. Guárdalo en el worker.
             */
            token: string;
            worker: components["schemas"]["WorkerOut"];
        };
        /** WorkerCreateRequest */
        WorkerCreateRequest: {
            /** Name */
            name: string;
            /** Queues */
            queues: components["schemas"]["Queue"][];
        };
        /** WorkerHeartbeat */
        WorkerHeartbeat: {
            capabilities: components["schemas"]["WorkerCapabilities"];
            /** Hostname */
            hostname: string;
            /** Platform */
            platform: string;
            /** Version */
            version: string;
        };
        /** WorkerHeartbeatAck */
        WorkerHeartbeatAck: {
            /** Contract Version */
            contract_version: number;
            /** Name */
            name: string;
            /** Queues */
            queues: string[];
            /**
             * Server Time
             * Format: date-time
             */
            server_time: string;
            /**
             * Worker Id
             * Format: uuid
             */
            worker_id: string;
        };
        /** WorkerOut */
        WorkerOut: {
            /** Capabilities */
            capabilities: {
                [key: string]: unknown;
            };
            /**
             * Created At
             * Format: date-time
             */
            created_at: string;
            /** Hostname */
            hostname: string | null;
            /**
             * Id
             * Format: uuid
             */
            id: string;
            /** Last Seen At */
            last_seen_at: string | null;
            /** Name */
            name: string;
            /**
             * Online
             * @default false
             */
            online: boolean;
            /** Platform */
            platform: string | null;
            /** Queues */
            queues: string[];
            /** Revoked At */
            revoked_at: string | null;
            /**
             * Status
             * @enum {string}
             */
            status: "active" | "revoked";
            /** Token Prefix */
            token_prefix: string;
            /** Version */
            version: string | null;
        };
        /** WorkersStatus */
        WorkersStatus: {
            /** Active */
            active: number;
            /** Online */
            online: number;
            /** Online Names */
            online_names: string[];
        };
    };
    responses: never;
    parameters: never;
    requestBodies: never;
    headers: never;
    pathItems: never;
}
export type $defs = Record<string, never>;
export interface operations {
    list_audit_events: {
        parameters: {
            query?: {
                action?: string | null;
                before?: number | null;
                limit?: number;
                outcome?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["AuditListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    login: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["LoginRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MeOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    logout: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
        };
    };
    me: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MeOut"];
                };
            };
        };
    };
    change_password: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PasswordChangeRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_brand_assets: {
        parameters: {
            query?: {
                kind?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandAssetOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_brand_asset: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandAssetOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_brand_asset: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BrandUpdateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandAssetOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_brand_asset: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandAssetOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    brand_download_url: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DownloadUrlOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    start_brand_upload: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["BrandUploadRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandUploadOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete_brand_upload: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["BrandAssetOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    download_url: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                object_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DownloadUrlOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    live: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthOut"];
                };
            };
        };
    };
    ready: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthOut"];
                };
            };
            /** @description Dependencia crítica caída */
            503: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HealthOut"];
                };
            };
        };
    };
    list_jobs: {
        parameters: {
            query?: {
                before?: string | null;
                limit?: number;
                status?: components["schemas"]["JobStatus"] | null;
                type?: string | null;
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_job: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancel_job: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    retry_job: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_media_assets: {
        parameters: {
            query?: {
                consent?: ("not_required" | "pending" | "granted" | "denied") | null;
                has_audio?: boolean | null;
                include_archived?: boolean;
                limit?: number;
                offset?: number;
                orientation?: ("vertical" | "horizontal" | "square") | null;
                q?: string | null;
                status?: string | null;
                tag?: string[];
            };
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaListOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    get_media_asset: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaAssetDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_media_asset: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaUpdateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaAssetDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    archive_media_asset: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaAssetDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_original_url: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["DownloadUrlOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_media_rights: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaRightsRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaAssetDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_waveform: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WaveformOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_media_tags: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["TagCountOut"][];
                };
            };
        };
    };
    start_media_upload: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["MediaUploadRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaUploadOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    abort_media_upload: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaAssetOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete_media_upload: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["MediaAssetDetailOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    media_upload_parts: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                asset_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["PartUrlsRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["PartUrlOut"][];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    render_engine: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RenderEngineOut"];
                };
            };
        };
    };
    create_evaluation_render: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["RemotionEvalRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    create_timeline_render: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["TimelineRenderRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    render_selftest: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["SelftestRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    system_status: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["SystemStatusOut"];
                };
            };
        };
    };
    list_users: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"][];
                };
            };
        };
    };
    create_user: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    update_user: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserUpdateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["UserOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    reset_password: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                user_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["UserPasswordResetRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_roles: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["RoleInfo"][];
                };
            };
        };
    };
    heartbeat: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkerHeartbeat"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkerHeartbeatAck"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    cancelled: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobTransitionAck"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    complete: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["CompleteRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobTransitionAck"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    fail: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["FailRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["JobTransitionAck"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    request_output: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["OutputUploadRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["OutputUploadTicket"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    progress: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                job_id: string;
            };
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ProgressReport"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["LeaseAck"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    claim: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["ClaimRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["ClaimedJob"];
                };
            };
            /** @description No hay trabajos disponibles en el tiempo de espera */
            204: {
                headers: {
                    [name: string]: unknown;
                };
                content?: never;
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    list_workers: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkerOut"][];
                };
            };
        };
    };
    register_worker: {
        parameters: {
            query?: never;
            header?: never;
            path?: never;
            cookie?: never;
        };
        requestBody: {
            content: {
                "application/json": components["schemas"]["WorkerCreateRequest"];
            };
        };
        responses: {
            /** @description Successful Response */
            201: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkerCreatedOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
    revoke_worker: {
        parameters: {
            query?: never;
            header?: never;
            path: {
                worker_id: string;
            };
            cookie?: never;
        };
        requestBody?: never;
        responses: {
            /** @description Successful Response */
            200: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["WorkerOut"];
                };
            };
            /** @description Validation Error */
            422: {
                headers: {
                    [name: string]: unknown;
                };
                content: {
                    "application/json": components["schemas"]["HTTPValidationError"];
                };
            };
        };
    };
}
