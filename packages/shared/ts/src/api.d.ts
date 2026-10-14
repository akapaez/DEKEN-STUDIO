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
            /**
             * Expires At
             * Format: date-time
             */
            expires_at: string;
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
        Permission: "system:read" | "system:manage" | "users:manage" | "workers:manage" | "audit:read" | "jobs:read" | "jobs:manage" | "files:read";
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
        /** WorkerCapabilities */
        WorkerCapabilities: {
            /** Encoders */
            encoders?: string[];
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
