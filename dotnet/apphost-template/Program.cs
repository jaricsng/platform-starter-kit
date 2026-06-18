// Aspire AppHost template
//
// Local dev:   dotnet run --project dotnet/apphost-template
// Cloud manifest (for CI reference or custom publishers):
//   dotnet run --project dotnet/apphost-template -- --publisher manifest --output-path aspire-manifest.json
//
// This file is a worked example wiring a Postgres-backed API + frontend.
// Replace the resource names, Dockerfile paths, and env vars below with
// your own services — the shape (parameters → resources → WaitFor →
// WithEnvironment) is the reusable part, not the specific resources.

var builder = DistributedApplication.CreateBuilder(args);

// ── Parameters ────────────────────────────────────────────────────────────────
// Defaults live in appsettings.Development.json (safe for dev only).
// In production, override via:
//   Azure:  azd env set <key> <value>  (stored in .azure/<env>/.env)
//   Local:  dotnet user-secrets set "Parameters:db-password" "..."
//   CI:     Parameters__db-password env var
var dbPassword  = builder.AddParameter("db-password",  secret: true);
var secretKey   = builder.AddParameter("secret-key",   secret: true);
var corsOrigins = builder.AddParameter("cors-origins");

// ── TODO: replace with your own data store(s) ──────────────────────────────────
var postgres = builder.AddPostgres("db", password: dbPassword)
    .WithDataVolume("app-data")
    .WithPgAdmin();   // pgAdmin UI at a random host port

// ── TODO: replace with your own API service ────────────────────────────────────
// AddDockerfile's second argument is the path to the directory containing
// the Dockerfile, relative to this AppHost project.
var pgEndpoint = postgres.GetEndpoint("tcp");
var api = builder.AddDockerfile("api", "../../path/to/your/api")
    .WithHttpEndpoint(port: 8000, name: "http")
    .WaitFor(postgres)
    // +asyncpg prefix required for Python's SQLAlchemy async driver — Aspire's
    // own WithReference(postgres) alone would inject the wrong format. See
    // claude-commands/check-aspire.md section 2c.
    .WithEnvironment("DATABASE_URL",
        ReferenceExpression.Create(
            $"postgresql+asyncpg://postgres:{dbPassword}@{pgEndpoint.Host}:{pgEndpoint.Port}/app"))
    .WithEnvironment("SECRET_KEY",   secretKey)
    .WithEnvironment("CORS_ORIGINS", corsOrigins)
    .WithEnvironment("OTEL_ENABLED", "true")
    .WithEnvironment("ENVIRONMENT",  "development");

// ── TODO: replace with your own frontend, or delete if API-only ────────────────
builder.AddDockerfile("frontend", "../../path/to/your/frontend")
    .WithHttpEndpoint(port: 5173, name: "http")
    .WaitFor(api)
    .WithEnvironment("VITE_API_URL", api.GetEndpoint("http"));

builder.Build().Run();
