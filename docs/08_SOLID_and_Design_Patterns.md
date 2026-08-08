# InsightFlow AI — SOLID Principles and Design Patterns

**Document:** `08_SOLID_and_Design_Patterns.md`  
**Status:** Draft / Foundational  
**Version:** 1.0  
**Last Updated:** 2026-08-08  
**Parent Documents:** `04_System_Architecture.md`, `05_System_Design.md`, `06_Database_Design.md`, `07_UI_UX_Design.md`

---

# 1. Purpose

This document defines the software engineering principles and design patterns that must guide InsightFlow AI implementation.

The primary purpose is to prevent the project from becoming tightly coupled as features are added by human developers or AI coding agents.

The rules in this document apply to:

- Production code.
- Tests.
- Infrastructure adapters.
- Application services.
- Domain logic.
- UI code.
- Future plugins.
- AI-generated code.

The goal is not to maximize the number of design patterns.

The goal is:

> **Use the simplest design that preserves separation of responsibility, testability, extensibility, and correctness.**

---

# 2. Core Engineering Principles

The project follows:

```text
SOLID
+
DRY
+
KISS
+
YAGNI
+
Separation of Concerns
+
Dependency Inversion
+
Explicit Boundaries
```

These principles must be balanced.

A design is not good merely because it uses many abstractions.

---

# 3. SOLID Overview

SOLID means:

```text
S — Single Responsibility Principle
O — Open/Closed Principle
L — Liskov Substitution Principle
I — Interface Segregation Principle
D — Dependency Inversion Principle
```

These principles are mandatory architectural guidance.

---

# 4. S — Single Responsibility Principle

## Definition

A class/module should have one primary responsibility and one reason to change.

Bad:

```text
GmailManager
    |
    +-- OAuth
    +-- Gmail API
    +-- Parse email
    +-- AI summary
    +-- Save database
    +-- Show popup
```

This class has too many responsibilities.

Preferred:

```text
GmailAuthenticator
GmailClient
GmailMessageNormalizer
AIAnalysisService
EventRepository
NotificationService
```

---

# 5. SRP Example

Instead of:

```python
class EmailProcessor:
    def process(self):
        gmail.fetch()
        ai.analyze()
        database.save()
        notification.show()
```

Prefer orchestration:

```python
class ProcessIntelligenceEvent:
    def execute(self, event_id):
        event = self.event_repository.get(event_id)
        analysis = self.ai_service.analyze(event)
        self.event_service.complete(event, analysis)
        self.notification_service.notify(event, analysis)
```

The use case coordinates.

Individual components own their specific responsibilities.

---

# 6. SRP for UI

A widget should not:

```text
Call Gmail
Call AI
Execute SQL
Apply business rules
```

A UI component should primarily:

```text
Display state
Collect user input
Send commands
```

---

# 7. O — Open/Closed Principle

Software entities should be open for extension but closed for modification.

Example:

Adding:

```text
OpenAI
```

should not require rewriting:

```text
AIAnalysisService
```

Instead:

```text
AIProvider
   |
   +-- BedrockAIProvider
   +-- OpenAIProvider
   +-- GeminiProvider
```

---

# 8. OCP Example — Source Providers

Current:

```text
GmailSourceProvider
```

Future:

```text
RSSSourceProvider
NewsAPIProvider
YouTubeSourceProvider
```

The common processing pipeline should not change merely because a new source is added.

---

# 9. OCP Example — Notifications

Current:

```text
WindowsNotificationProvider
```

Future:

```text
TelegramNotificationProvider
SlackNotificationProvider
EmailNotificationProvider
```

The notification service should depend on:

```text
NotificationProvider
```

rather than a concrete Windows implementation.

---

# 10. L — Liskov Substitution Principle

Any implementation of an interface must be usable wherever that interface is expected without breaking application behavior.

If:

```text
AIProvider
```

is implemented by:

```text
BedrockAIProvider
OpenAIProvider
```

both must honor the same contract.

A provider must not unexpectedly:

- Return incompatible structures.
- Ignore required fields.
- Change error semantics arbitrarily.
- Require undocumented behavior.

---

# 11. LSP Example

Bad:

```text
AIProvider.analyze()
```

Bedrock returns structured analysis.

OpenAI implementation returns a completely unrelated raw string.

This violates the intended contract.

Preferred:

```text
All providers
    |
    v
Provider-independent AIResponse
```

---

# 12. I — Interface Segregation Principle

Do not create huge interfaces.

Bad:

```python
class Provider:
    connect()
    fetch_events()
    analyze()
    notify()
    download()
    publish()
```

A Gmail provider does not need to implement AI, notification, and publishing.

Prefer:

```text
SourceProvider
AIProvider
NotificationProvider
AttachmentProcessor
ContentPublisher
```

---

# 13. Small Interfaces

Good interfaces should represent one capability.

Examples:

```text
EventReader
EventRepository
AIProvider
NotificationProvider
SecretStore
AttachmentStorage
```

---

# 14. D — Dependency Inversion Principle

High-level application logic must depend on abstractions, not concrete infrastructure.

Bad:

```python
class AIAnalysisService:
    def __init__(self):
        self.client = boto3.client(...)
```

Preferred:

```python
class AIAnalysisService:
    def __init__(self, provider: AIProvider):
        self.provider = provider
```

Concrete provider selection occurs in the composition root.

---

# 15. Dependency Direction

Correct:

```text
Application
    |
    v
AIProvider interface
    ^
    |
BedrockAIProvider
```

Incorrect:

```text
Application
    |
    v
BedrockAIProvider
```

---

# 16. DRY — Don't Repeat Yourself

Shared business logic must have one authoritative implementation.

Examples:

Do not implement priority logic separately in:

```text
Dashboard
Notification
Rules
Database
```

Instead:

```text
PriorityEngine
```

owns the logic.

---

# 17. DRY Warning

DRY does not mean every two similar lines must become an abstraction.

Premature abstraction can be worse than small duplication.

Use DRY when the duplicated behavior represents the same business concept.

---

# 18. KISS — Keep It Simple

Prefer:

```text
Simple class
Simple interface
Simple flow
```

over:

```text
FactoryBuilderStrategyProviderManager
```

when a simple implementation is sufficient.

---

# 19. YAGNI — You Aren't Gonna Need It

Do not implement future infrastructure merely because it might be useful.

Examples not required in MVP:

```text
Microservices
Kafka
Kubernetes
Distributed cache
Multi-region database
Cloud API gateway
```

unless a real requirement appears.

---

# 20. Pattern Selection Rule

Before introducing a design pattern, ask:

```text
What problem does this solve?

Is the problem actually present?

Does the pattern reduce complexity?

Will it improve testability or extensibility?

Could a simpler design solve it?
```

If a pattern adds more complexity than value, do not use it.

---

# 21. Required Patterns

The following patterns are recommended/required where applicable:

```text
Dependency Injection
Repository
Adapter
Strategy
Factory / Factory Method
Unit of Work
State Machine
Specification / Rule
Observer / Domain Events
Facade
DTO
```

Not every pattern must appear in every module.

---

# 22. Dependency Injection Pattern

Dependency Injection is a core architectural mechanism.

Example:

```text
ProcessEventService
    |
    +--> EventRepository
    +--> TopicResolver
    +--> AIProvider
    +--> PriorityEngine
    +--> NotificationService
```

Dependencies are supplied from outside.

---

# 23. Constructor Injection

Preferred:

```python
class ProcessEventService:
    def __init__(
        self,
        event_repository: EventRepository,
        ai_provider: AIProvider,
    ):
        ...
```

Avoid hidden dependencies.

---

# 24. Avoid Service Locator

Do not use:

```python
container.get("AIProvider")
```

throughout application code.

This hides dependencies.

Prefer explicit constructor dependencies.

---

# 25. Composition Root

Concrete implementations should be assembled in one place.

Example:

```text
main.py
    |
    v
ApplicationContainer
    |
    +--> SQLiteEventRepository
    +--> GmailSourceProvider
    +--> BedrockAIProvider
    +--> WindowsNotificationProvider
```

---

# 26. Repository Pattern

Repositories abstract persistence.

Example:

```text
EventRepository
       |
       v
SQLiteEventRepository
```

Application code does not know SQL.

---

# 27. Repository Responsibilities

Repositories handle:

```text
Save
Find
Update
Delete where appropriate
Query
```

Repositories do not handle:

```text
AI
Notifications
Gmail
Business workflows
UI
```

---

# 28. Repository Anti-Pattern

Avoid repositories that become business-service classes.

Bad:

```text
EventRepository.generate_ai_summary()
```

AI is not persistence responsibility.

---

# 29. Adapter Pattern

Adapters translate external APIs into internal interfaces.

Example:

```text
Gmail SDK
   |
   v
GmailAdapter
   |
   v
SourceProvider
```

---

# 30. Adapter Responsibilities

An adapter should:

- Translate external request/response models.
- Handle provider-specific API behavior.
- Convert provider errors.
- Hide SDK details.

An adapter should not implement application workflows.

---

# 31. AI Adapter

Example:

```text
AIProvider
    ^
    |
BedrockAIProvider
    |
    v
boto3 / Bedrock SDK
```

The Bedrock SDK must not leak into the application layer.

---

# 32. Strategy Pattern

Use Strategy when behavior is intentionally interchangeable.

Good examples:

```text
PriorityStrategy
NotificationStrategy
DeduplicationStrategy
StoryMatchingStrategy
```

Example:

```text
PriorityPolicy
   |
   +-- RuleBasedPriority
   +-- AIEnhancedPriority
```

---

# 33. Strategy Warning

Do not create a strategy interface merely because two functions exist.

Use Strategy when the application genuinely needs interchangeable algorithms.

---

# 34. Factory Pattern

Factories may be used when object creation is non-trivial.

Example:

```text
AIProviderFactory
      |
      +-- Bedrock
      +-- OpenAI
      +-- Gemini
```

---

# 35. Factory Rule

Do not create factories for trivial constructors.

Bad:

```python
UserFactory.create_user(name)
```

if it simply executes:

```python
return User(name)
```

A factory is justified when creation depends on:

- Configuration.
- Provider selection.
- Validation.
- Multiple implementations.
- Complex construction.

---

# 36. Unit of Work Pattern

Use Unit of Work to coordinate related persistence operations.

Example:

```text
BEGIN
    update event
    save analysis
    update processing state
    create notification
COMMIT
```

---

# 37. Unit of Work Rule

Do not hold a database transaction while:

```text
Calling Gmail
Calling AI
Downloading files
Waiting for network
```

Transactions must remain short.

---

# 38. State Machine Pattern

Processing lifecycle is naturally represented by a state machine.

```text
RECEIVED
    |
VALIDATING
    |
NORMALIZED
    |
AI_PENDING
    |
AI_PROCESSING
    |
AI_COMPLETED
    |
COMPLETED
```

Failure branches:

```text
RETRY_PENDING
FAILED
DUPLICATE
IGNORED
```

---

# 39. State Machine Responsibilities

The state machine should define:

```text
Valid states
Valid transitions
Invalid transitions
Recovery transitions
```

Example:

```text
COMPLETED -> AI_PROCESSING
```

should not be allowed unless an explicit reprocessing workflow requests it.

---

# 40. State Machine Anti-Pattern

Do not scatter state transitions throughout the code.

Bad:

```python
record.status = "COMPLETED"
```

in dozens of unrelated modules.

Prefer:

```text
ProcessingStateMachine.transition(...)
```

or an equivalent domain method.

---

# 41. Specification Pattern

The Specification/Rule pattern is useful for configurable conditions.

Example:

```text
Topic = TRUMP
AND
Priority >= HIGH
```

can be represented as specifications.

---

# 42. Rule Composition

Specifications may support:

```text
AND
OR
NOT
```

Example:

```text
HighPriority
AND
TopicIs("TRUMP")
```

---

# 43. Rule Engine

Future workflow rules:

```text
IF condition
THEN action
```

should use a dedicated rule model.

Do not embed user-created rules as Python code.

---

# 44. Observer / Domain Events

Use events when one component needs to react without tightly coupling the publisher to the consumer.

Example:

```text
AIAnalysisCompleted
        |
        +--> Notification handler
        +--> Story handler
        +--> Metrics handler
```

---

# 45. Event Usage Rule

Do not use the event bus for every method call.

Prefer direct calls when:

```text
A needs result from B
```

Use events when:

```text
A announces something happened
B/C/D may independently react
```

---

# 46. Domain Events

Potential domain events:

```text
IntelligenceEventReceived
AIAnalysisCompleted
PriorityChanged
NotificationRequested
StoryUpdated
ContentJobRequested
```

---

# 47. External Events

External events are different:

```text
Gmail Pub/Sub notification
```

They must first be validated and translated into internal concepts.

---

# 48. DTO Pattern

Data Transfer Objects should cross architectural boundaries.

Examples:

```text
EventSummaryDTO
EventDetailsDTO
TopicDTO
NotificationDTO
AIAnalysisDTO
```

This prevents UI code from becoming dependent on domain internals.

---

# 49. DTO Rule

DTOs should be simple data structures.

Do not put substantial business logic inside DTOs.

---

# 50. Domain Entity vs DTO

Use:

```text
Domain Entity
```

for business behavior.

Use:

```text
DTO
```

for communication between layers.

Example:

```text
Event entity
      |
      v
EventDetailsDTO
      |
      v
ViewModel
      |
      v
UI
```

---

# 51. Facade Pattern

A facade can provide a simplified interface to a complex subsystem.

Example:

```text
GmailMonitoringFacade
```

could coordinate:

```text
OAuth
Watch
Pub/Sub
Message retrieval
Label handling
```

However, the facade should delegate rather than become a god class.

---

# 52. Facade Rule

A facade is appropriate when it reduces complexity for callers.

It must not become:

```text
EverythingManager
```

---

# 53. Template Method

Generally avoid Template Method when Strategy/composition can achieve the same goal.

Inheritance should not be the default extensibility mechanism.

Prefer composition.

---

# 54. Inheritance Rule

Use inheritance primarily for:

```text
Stable abstraction
Shared contract
True substitutability
```

Prefer:

```text
composition
delegation
protocols/interfaces
```

for most provider behavior.

---

# 55. Abstract Base Classes vs Protocols

Python protocols are preferred when structural typing is sufficient.

Example:

```python
class AIProvider(Protocol):
    def analyze(self, request: AIRequest) -> AIResponse:
        ...
```

Use abstract base classes when:

- Shared implementation is required.
- Runtime inheritance semantics are useful.
- Common lifecycle behavior exists.

---

# 56. Null Object Pattern

A Null Object may be useful for optional components.

Example:

```text
NullNotificationProvider
```

when notifications are disabled.

This can avoid repeated:

```python
if notification_provider is not None:
```

but should only be used where it improves clarity.

---

# 57. Command Pattern

Commands are useful for user/application actions.

Examples:

```text
CreateTopicCommand
PauseTopicCommand
RetryEventCommand
ReprocessAICommand
DeleteHistoryCommand
```

This can make UI actions explicit and testable.

---

# 58. Query Pattern

Read operations should be separated from commands where useful.

Examples:

```text
GetDashboardQuery
SearchEventsQuery
GetEventDetailsQuery
GetTopicListQuery
GetSystemHealthQuery
```

Commands change state.

Queries retrieve information.

---

# 59. CQRS Guidance

Full CQRS is not required.

Use the lightweight distinction:

```text
Command = changes state
Query   = reads state
```

Do not introduce separate read/write databases for MVP.

---

# 60. Event Sourcing

Event sourcing is explicitly **not required**.

The application already stores:

```text
Events
Processing
AI Analysis
Audit
```

There is no need to reconstruct the entire application state from an event log.

---

# 61. Microservices Pattern

Microservices are explicitly **not required** for MVP.

The system is a modular monolith.

---

# 62. Repository + Unit of Work

These patterns should work together:

```text
Application Service
       |
       v
UnitOfWork
       |
       +--> EventRepository
       +--> AIAnalysisRepository
       +--> NotificationRepository
       |
       v
SQLite
```

---

# 63. Adapter + Strategy

Provider architecture may combine both:

```text
AIProvider
   |
   +--> Bedrock Adapter
   +--> OpenAI Adapter
   +--> Gemini Adapter
```

Provider selection is a configuration/strategy decision.

---

# 64. State Machine + Repository

The state machine controls valid transitions.

The repository persists the result.

```text
State Machine
      |
      v
New State
      |
      v
Repository
```

The repository should not decide business validity of the transition.

---

# 65. Rules + Strategy

Priority and notification behavior can use policies.

Example:

```text
PriorityPolicy
      |
      +--> TradingPriorityPolicy
      +--> GeneralNewsPriorityPolicy
```

However, the user should normally configure policies through data rather than requiring a new Python class for every topic.

---

# 66. Data-Driven Design

This is especially important for topics.

Do not create:

```text
TrumpProcessor
IranProcessor
ModiProcessor
CelebrityProcessor
```

Instead:

```text
Topic
 +
AI Profile
 +
Rules
```

determine behavior.

---

# 67. Example of Correct Generic Design

```text
Incoming Event
      |
      v
Topic = TRUMP
      |
      v
AI Profile = Trading/Geopolitics
      |
      v
Generic Processing Pipeline
      |
      v
Trading-oriented analysis
```

For another topic:

```text
Topic = CELEBRITY_X
      |
      v
AI Profile = Entertainment
      |
      v
Same Generic Processing Pipeline
```

---

# 68. Dependency Injection Example

Conceptual:

```python
class ProcessEventService:
    def __init__(
        self,
        event_repository: EventRepository,
        topic_repository: TopicRepository,
        ai_provider: AIProvider,
        priority_engine: PriorityEngine,
        notification_service: NotificationService,
    ):
        ...
```

Tests can inject:

```text
FakeEventRepository
FakeAIProvider
FakeNotificationService
```

---

# 69. Testing Design Patterns

Patterns should improve testability.

Example:

```text
AIProvider
   |
   +-- BedrockAIProvider
   +-- FakeAIProvider
```

This lets tests execute without AWS.

---

# 70. Fake vs Mock

Prefer simple fakes for complex provider behavior.

Example:

```text
FakeAIProvider
    returns predefined AIResponse
```

Use mocks when verifying a specific interaction is important.

Do not mock every class.

---

# 71. Testability Rule

If a class is difficult to unit test because it directly creates:

```text
AWS client
Gmail client
database
filesystem
UI widget
```

the design probably violates Dependency Inversion.

---

# 72. Pattern for Time

Use:

```text
Clock
```

interface.

Production:

```text
SystemClock
```

Tests:

```text
FakeClock
```

This supports deterministic tests for:

```text
Quiet hours
Retry
Retention
Notification duration
Story grouping
```

---

# 73. Pattern for File Storage

Use:

```text
AttachmentStorage
```

implementations:

```text
LocalAttachmentStorage
FakeAttachmentStorage
FutureCloudAttachmentStorage
```

---

# 74. Pattern for Secrets

Use:

```text
SecretStore
```

implementations:

```text
WindowsSecretStore
FakeSecretStore
```

---

# 75. Pattern for Notifications

Use:

```text
NotificationProvider
```

implementations:

```text
WindowsNotificationProvider
FakeNotificationProvider
FutureTelegramProvider
```

---

# 76. Pattern for Source Integration

Use:

```text
SourceProvider
```

implementations:

```text
GmailSourceProvider
FutureRSSProvider
FutureNewsAPIProvider
```

---

# 77. Pattern for Attachments

Use:

```text
AttachmentProcessor
```

implementations:

```text
PdfProcessor
ExcelProcessor
CsvProcessor
ImageProcessor
ZipProcessor
```

The attachment orchestrator should select the appropriate processor.

---

# 78. Attachment Processor Factory

A factory/registry is appropriate here.

Conceptually:

```text
MIME type
    |
    v
AttachmentProcessorRegistry
    |
    +--> application/pdf -> PdfProcessor
    +--> spreadsheet -> ExcelProcessor
    +--> text/csv -> CsvProcessor
```

Unsupported types return:

```text
UnsupportedAttachmentProcessor
```

or an explicit unsupported result.

---

# 79. Pattern for AI Output Validation

Use a dedicated validator:

```text
AIResponse
    |
    v
AIOutputValidator
    |
    v
ValidatedAIAnalysis
```

Do not mix schema validation into every provider adapter.

---

# 80. Pattern for Prompt Building

Use a dedicated:

```text
PromptBuilder
```

It combines:

```text
AI Profile
Profile Version
Topic Context
Source Content
Output Schema
```

The provider receives the resulting `AIRequest`.

---

# 81. Prompt Builder Strategy

Different profile types may require different prompt construction.

If genuinely necessary:

```text
PromptBuilder
    |
    +--> DefaultPromptBuilder
    +--> StructuredAnalysisPromptBuilder
```

Do not create one class per topic.

---

# 82. Pattern for Priority

Use a policy/strategy:

```text
PriorityEngine
      |
      +--> Topic policy
      +--> Rule evaluation
      +--> AI signals
```

The UI must never calculate priority.

---

# 83. Pattern for Notification Policy

Use:

```text
NotificationPolicy
```

to determine:

```text
Should notify?
Which priority?
Quiet hours?
Duplicate suppression?
```

The Windows popup only renders the result.

---

# 84. Pattern for Configuration

Use typed configuration objects.

Example:

```text
GmailSettings
AISettings
NotificationSettings
AttachmentSettings
StorageSettings
```

Avoid a codebase full of:

```python
config["something"]["another"]["value"]
```

---

# 85. Configuration Factory

The application composition root may construct configuration from:

```text
Defaults
+
User settings
+
Environment
```

Secrets are resolved separately.

---

# 86. Pattern for Health Checks

Use a common health contract:

```text
HealthCheck
```

Implementations:

```text
GmailHealthCheck
AIHealthCheck
DatabaseHealthCheck
NotificationHealthCheck
```

The dashboard aggregates results.

---

# 87. Health Check Rule

Health checks must be lightweight.

Do not perform expensive AI calls merely to determine whether AI is configured.

---

# 88. Pattern for Retry

Use a centralized:

```text
RetryPolicy
```

It determines:

```text
Is retryable?
Maximum attempts
Backoff
Next retry time
```

Avoid custom retry loops in every adapter.

---

# 89. Pattern for Error Translation

Adapters translate:

```text
Provider Exception
```

into:

```text
Application/Infrastructure Error
```

Example:

```text
Google API RefreshError
      |
      v
GmailAuthenticationError
```

---

# 90. Pattern for Logging

Use structured logging through the application's logging boundary.

Log context:

```text
correlation_id
event_id
topic_id
operation
duration
status
```

Do not log secrets.

---

# 91. Pattern for Correlation

Every significant processing operation should carry a correlation ID.

Example:

```text
CORR-20260808-000123
```

This ID should appear in logs and processing records.

---

# 92. Pattern for Audit

Use a dedicated:

```text
AuditService
```

rather than writing audit SQL from individual UI widgets.

---

# 93. Pattern for Search

Use:

```text
SearchService
```

over repositories/search indexes.

The UI sends:

```text
SearchQuery
```

and receives:

```text
SearchResult
```

---

# 94. Pattern for Story Matching

Start simple.

MVP:

```text
DeterministicStoryMatcher
```

Future:

```text
SemanticStoryMatcher
```

Both can implement:

```text
StoryMatcher
```

if the need for interchangeable matching becomes real.

---

# 95. Pattern for Content Generation

Use provider interfaces:

```text
ScriptGenerator
VoiceGenerator
ImageGenerator
VideoGenerator
Publisher
```

Each can have multiple implementations.

---

# 96. Pattern for Publishing

Future:

```text
Publisher
   |
   +--> YouTubePublisher
   +--> FutureTikTokPublisher
   +--> FutureOtherPublisher
```

The content pipeline must not depend directly on the YouTube SDK.

---

# 97. Pattern for Workflows

A workflow can be modeled as:

```text
Trigger
   |
   v
Conditions
   |
   v
Actions
```

Actions should use existing application services.

Do not allow workflow definitions to execute arbitrary Python code.

---

# 98. Security Rule for Rules

User-defined rules must be data-driven.

Never implement:

```text
eval(user_rule)
exec(user_rule)
```

or equivalent arbitrary code execution.

---

# 99. Pattern for Notification Queue

Use a queue abstraction:

```text
NotificationQueue
```

The queue separates:

```text
Notification requested
```

from:

```text
Notification displayed
```

---

# 100. Pattern for Processing Queue

Use:

```text
ProcessingQueue
```

to decouple:

```text
Event received
```

from:

```text
Event processed
```

This is especially important for real-time bursts.

---

# 101. Queue Rule

Queues should have bounded concurrency.

Do not spawn unlimited workers.

---

# 102. Pattern for Application Lifecycle

A dedicated:

```text
ApplicationLifecycleManager
```

may coordinate:

```text
Startup
Connection
Monitoring
Shutdown
```

It must not own every application feature.

---

# 103. Pattern for System Tray

System tray should communicate with application commands.

Bad:

```text
Tray -> Gmail API
```

Good:

```text
Tray
  |
  v
PauseMonitoringCommand
  |
  v
MonitoringService
```

---

# 104. UI Command Pattern

UI actions should map to explicit commands.

Examples:

```text
CreateTopicCommand
PauseTopicCommand
RetryEventCommand
OpenSourceCommand
DeleteHistoryCommand
```

This makes UI behavior testable.

---

# 105. ViewModel Pattern

ViewModels transform application DTOs into UI state.

```text
Application DTO
      |
      v
ViewModel
      |
      v
PySide6 Widget
```

---

# 106. ViewModel Rule

ViewModels must not:

```text
Call Gmail SDK
Call Bedrock
Execute SQL
Modify domain entities directly without use-case coordination
```

---

# 107. Dependency Rule for UI

```text
Widget
  |
  v
ViewModel/Controller
  |
  v
Application Use Case
  |
  v
Domain
```

---

# 108. Pattern Combination Example

The main processing path may combine several patterns:

```text
Pub/Sub Adapter
      |
      v
Event Handler
      |
      v
ProcessEventUseCase
      |
      +--> Repository
      +--> TopicResolver
      +--> AIProvider Strategy
      +--> Priority Policy
      +--> UnitOfWork
      |
      v
Domain Event
      |
      +--> Notification Queue
      +--> Story Service
      +--> Metrics
```

This is a valid combination because each pattern solves a distinct problem.

---

# 109. Pattern Overuse Warning

Avoid designs such as:

```text
IEventProcessorFactoryProviderStrategyManager
```

when one class could solve the problem.

Patterns are tools, not goals.

---

# 110. AI Agent-Specific Rule

AI coding agents often over-abstract.

Therefore agents must not:

```text
Create interfaces for every class
Create factories for every constructor
Create managers for every feature
Create base classes without shared behavior
Create event buses for simple calls
```

---

# 111. AI Agent Decision Rule

Before creating an abstraction, the agent must be able to answer:

```text
What concrete variation exists today or is explicitly required?

What dependency needs to be inverted?

What testability problem does this solve?

What future extension is specified?
```

If there is no clear answer, prefer a simpler implementation.

---

# 112. AI Agent Refactoring Rule

If the existing design already has a suitable:

```text
Repository
Provider
Service
Policy
Factory
```

the agent must reuse it rather than creating another abstraction with a similar purpose.

---

# 113. Interface Naming Rules

Prefer:

```text
AIProvider
EventRepository
NotificationProvider
AttachmentStorage
TopicResolver
PriorityEngine
```

Avoid vague:

```text
IManager
IHelper
IUtility
ICommonService
```

unless the responsibility is genuinely clear.

---

# 114. Class Naming

Classes should represent:

```text
Entity
Value Object
Use Case
Service
Repository
Provider
Adapter
Policy
Strategy
Factory
Validator
Mapper
DTO
ViewModel
```

Names should communicate responsibility.

---

# 115. Method Naming

Methods should describe actions.

Good:

```text
process_event()
analyze()
save()
find_by_external_id()
calculate_priority()
should_notify()
```

Avoid:

```text
do_it()
handle()
process_data()
run()
execute()
```

unless the surrounding type provides enough context.

---

# 116. Method Size

Methods should remain small enough to understand.

If a method contains:

```text
validation
database
network
AI
notification
```

it likely contains multiple responsibilities.

---

# 117. Class Size

There is no universal line-count limit.

However, a class should be reviewed when it:

- Has many unrelated methods.
- Has many dependencies.
- Changes for unrelated reasons.
- Requires extensive mocking.
- Owns multiple external resources.

---

# 118. Dependency Count

A class with many injected dependencies is a warning signal.

Example:

```text
15 constructor dependencies
```

may indicate that orchestration should be decomposed.

Do not blindly split it; first identify the actual responsibilities.

---

# 119. Circular Dependency Rule

Circular dependencies between modules are prohibited.

Example:

```text
application -> infrastructure -> application
```

should be avoided through interfaces and dependency inversion.

---

# 120. Import Boundary

The codebase should enforce import direction through:

```text
Linting
Architecture tests
Code review
```

where practical.

---

# 121. Architecture Tests

Future automated architecture tests should verify:

```text
Domain cannot import infrastructure
Domain cannot import presentation
Application cannot import PySide6
Application cannot import provider SDKs
```

---

# 122. Testing Pattern

A typical unit test:

```text
Use Case
  |
  +--> Fake Repository
  +--> Fake AI Provider
  +--> Fake Notification Provider
```

This makes tests fast and deterministic.

---

# 123. Integration Test Pattern

Integration tests may use:

```text
Real SQLite
Fake/controlled external provider
```

rather than mocking every layer.

---

# 124. End-to-End Pattern

An E2E test should validate:

```text
Input Event
   |
   v
Processing
   |
   v
AI
   |
   v
Persistence
   |
   v
Notification
```

Use a controlled test environment.

---

# 125. Database Pattern

The database layer should use:

```text
Repository
+
Unit of Work
+
Mapper
+
Migration
```

This keeps persistence concerns localized.

---

# 126. Mapping Pattern

Separate:

```text
Domain Model
Persistence Model
DTO
ViewModel
```

when their responsibilities differ.

Do not create unnecessary mapping layers for trivial objects.

---

# 127. Serialization Rule

External provider JSON must not automatically become the domain model.

It should pass through:

```text
Provider DTO
      |
      v
Normalizer/Mapper
      |
      v
Domain Model
```

---

# 128. Gmail-Specific Design

Gmail-specific concepts must remain in:

```text
infrastructure/gmail
```

Examples:

```text
GmailMessage
GmailLabel
GmailHistoryId
GmailWatch
```

The domain should use:

```text
IntelligenceEvent
Source
Topic
```

---

# 129. Bedrock-Specific Design

Bedrock-specific concepts remain in:

```text
infrastructure/ai
```

Examples:

```text
boto3 client
Bedrock request format
Bedrock response format
model-specific options
```

The application sees:

```text
AIRequest
AIResponse
AIAnalysis
```

---

# 130. Windows-Specific Design

Windows APIs belong in:

```text
infrastructure/notifications
presentation
```

as appropriate.

The domain should not know Windows APIs.

---

# 131. Pattern for Platform Abstraction

Where platform behavior may change:

```text
DesktopNotificationProvider
```

allows:

```text
Windows
macOS
Linux
```

in a future version.

---

# 132. Pattern for File Paths

Do not pass raw filesystem paths throughout the domain.

Use:

```text
StorageReference
```

or an equivalent abstraction where practical.

---

# 133. Pattern for URLs

Use a validated URL/value object when URL correctness matters.

Do not blindly treat every external string as a trusted URL.

---

# 134. Pattern for Email Addresses

If email addresses are used as domain concepts, use a validated value object rather than repeated string validation.

---

# 135. Pattern for Priority

Priority should be a domain concept.

Example:

```text
Priority.LOW
Priority.MEDIUM
Priority.HIGH
Priority.CRITICAL
```

Do not scatter string comparisons:

```python
if priority == "HIGH":
```

throughout the application.

---

# 136. Pattern for Processing Status

Use an enum/value object/state machine.

Do not scatter raw strings:

```python
status = "AI_PROCESSING"
```

throughout the codebase.

---

# 137. Pattern for Configuration

Use typed configuration models.

For example:

```text
GmailConfig
AIConfig
NotificationConfig
AttachmentConfig
StorageConfig
```

This improves validation and readability.

---

# 138. Pattern for Feature Flags

Feature flags may be used for:

```text
Stories
Content generation
Experimental AI features
```

But feature flags should not become permanent substitutes for proper architecture.

---

# 139. Pattern for Experimental Features

Experimental functionality should be isolated behind:

```text
Feature boundary
```

and must not destabilize the core monitoring pipeline.

---

# 140. Pattern for Plugin Registry

Future provider plugins may use a registry:

```text
ProviderRegistry
```

Example:

```text
"bedrock" -> BedrockAIProvider
"openai"  -> OpenAIProvider
```

The registry should be initialized in the composition root.

---

# 141. Plugin Rule

Plugins must implement established contracts.

A plugin must not modify unrelated domain logic.

---

# 142. Pattern for Health Status

Use a common:

```text
HealthStatus
```

value object containing:

```text
status
message
checked_at
details
```

---

# 143. Pattern for Error Types

Use explicit error types.

Example:

```text
GmailAuthenticationError
AIProviderUnavailableError
AIResponseValidationError
DatabaseUnavailableError
AttachmentTooLargeError
UnsupportedAttachmentError
```

This supports correct retry decisions.

---

# 144. Pattern for Retryable Errors

Errors may expose:

```text
retryable = True/False
```

or be classified through a dedicated error classifier.

The retry mechanism must not inspect arbitrary error message strings.

---

# 145. Pattern for Notifications

A notification should be a domain/application object first.

The Windows popup is only one presentation mechanism.

---

# 146. Pattern for Content Jobs

Content generation should be asynchronous.

Use:

```text
ContentJob
+
ContentService
+
Provider interfaces
```

rather than blocking the event processing pipeline.

---

# 147. Pattern for Long-Running Jobs

Long-running operations should use:

```text
Job
Queue
Worker
Status
Persistence
```

This applies to future:

```text
Video generation
Large attachment processing
Batch AI analysis
```

---

# 148. Pattern for User Preferences

User preferences belong in configuration/settings, not scattered through widgets.

---

# 149. Pattern for Audit

Important state changes should use:

```text
AuditService
```

which persists:

```text
Actor
Action
Entity
Timestamp
Details
```

---

# 150. Pattern for Observability

Metrics and logging should not become business dependencies.

Use thin abstractions where needed.

---

# 151. Anti-Pattern: God Object

Forbidden:

```text
InsightFlowManager
```

containing every feature.

If a class begins to control:

```text
Gmail
AI
Database
Notifications
UI
Attachments
YouTube
```

it must be decomposed.

---

# 152. Anti-Pattern: Anemic Domain Overcorrection

Do not move every piece of logic into application services merely to keep entities empty.

Entities/value objects should own meaningful domain invariants and behavior where appropriate.

---

# 153. Anti-Pattern: Overusing Static Methods

Static utility methods should not be used to avoid dependency injection.

Prefer objects when behavior depends on:

```text
Configuration
Providers
State
Time
External services
```

---

# 154. Anti-Pattern: Global Singleton

Avoid global mutable singleton objects for:

```text
Database
AI provider
Configuration
Current user
Application state
```

The composition root should control lifecycle.

---

# 155. Anti-Pattern: Hidden Dependency

Bad:

```python
def process():
    global ai_provider
```

Good:

```python
class Processor:
    def __init__(self, ai_provider):
        ...
```

---

# 156. Anti-Pattern: Catch Everything

Avoid:

```python
except Exception:
    pass
```

Errors must be:

```text
Handled
Translated
Logged
Retried
or Propagated
```

appropriately.

---

# 157. Anti-Pattern: Business Logic in Database Queries

Avoid encoding complex business rules entirely in SQL.

Business rules belong in the domain/application layer.

SQL should efficiently retrieve/persist data.

---

# 158. Anti-Pattern: Business Logic in AI Prompt

AI prompts may guide interpretation, but deterministic application rules must remain in code.

For example:

```text
"Do not notify on LOW"
```

should not rely solely on the AI prompt.

The application notification policy must enforce it.

---

# 159. AI Is Not a Source of Truth

AI output is an analysis result.

The application must not allow AI to override deterministic facts such as:

```text
Event identity
Timestamp
Topic configuration
Processing state
Notification suppression
User settings
Security policy
```

---

# 160. Pattern for AI + Deterministic Logic

Preferred:

```text
Source
  |
  v
Deterministic normalization
  |
  v
AI analysis
  |
  v
Deterministic validation
  |
  v
Deterministic priority/notification policy
```

---

# 161. Pattern for Human Approval

Future content workflows should use:

```text
Generated
    |
    v
Review
    |
    v
Approved
    |
    v
Published
```

Do not skip the approval state for important public content in the initial implementation.

---

# 162. Pattern for Versioning

Version:

```text
AI Profiles
Prompts
Database schema
Application configuration
Content templates
```

when historical reproducibility matters.

---

# 163. Pattern for Auditability

Every important AI analysis should be traceable to:

```text
Event
AI Profile
Profile Version
Provider
Model
Timestamp
```

---

# 164. Pattern for Reproducibility

A previous AI result should be explainable even if the model changes later.

Store sufficient metadata to identify:

```text
Which provider?
Which model?
Which profile?
Which prompt version?
```

---

# 165. Pattern for Future Model Changes

Changing:

```text
Claude model
```

must not require rewriting:

```text
Event processing
Notification
Database
UI
```

Only provider/model configuration should change where possible.

---

# 166. Pattern for Future Source Changes

Adding:

```text
RSS
```

must not require rewriting:

```text
AIAnalysisService
NotificationService
Dashboard
```

The source adapter produces the common event model.

---

# 167. Pattern for Future Notification Changes

Adding:

```text
Telegram
```

must not require rewriting:

```text
PriorityEngine
EventProcessor
TopicResolver
```

---

# 168. Pattern for Future Content Changes

Adding:

```text
3-minute YouTube Short
```

must not affect:

```text
Gmail monitoring
AI summary
Desktop notification
```

Content generation is a downstream workflow.

---

# 169. Architectural Pattern Summary

| Pattern | Use in InsightFlow |
|---|---|
| Dependency Injection | Required |
| Repository | Required for persistence |
| Adapter | Required for external providers |
| Strategy | For genuinely interchangeable algorithms |
| Factory | For complex/provider-dependent creation |
| Unit of Work | Database transaction coordination |
| State Machine | Processing lifecycle |
| Specification/Rule | User-configurable conditions |
| Observer/Events | Decoupled reactions |
| DTO | Layer boundaries |
| Facade | Simplifying complex subsystems |
| Command | User/application actions |
| Query | Read operations |
| Null Object | Optional capabilities where useful |
| Mapper | Domain/persistence/provider translation |
| Plugin Registry | Future provider extensibility |

---

# 170. Pattern Priority

If an AI agent is unsure which pattern to use, prioritize:

```text
1. Dependency Injection
2. Clear interfaces
3. Repository
4. Adapter
5. Simple composition
6. Strategy where variation exists
7. State Machine where lifecycle exists
8. Other patterns only when justified
```

---

# 171. Decision Hierarchy

When designing a component:

```text
Can a simple function solve it?
        |
       Yes -> Use function
        |
       No
        v
Can a simple class solve it?
        |
       Yes -> Use class
        |
       No
        v
Is there interchangeable behavior?
        |
       Yes -> Strategy
        |
       No
        v
Is there external integration?
        |
       Yes -> Adapter/Port
        |
       No
        v
Is persistence involved?
        |
       Yes -> Repository
        |
       No
        v
Is lifecycle/state complex?
        |
       Yes -> State Machine
        |
       No
        v
Choose the simplest remaining design.
```

---

# 172. AI Coding Agent Checklist

Before submitting code, an AI agent should check:

```text
[ ] Does each class have a clear responsibility?
[ ] Are external SDKs isolated?
[ ] Are dependencies injected?
[ ] Is existing abstraction reused?
[ ] Is business logic outside UI?
[ ] Is SQL outside application/domain?
[ ] Are provider implementations substitutable?
[ ] Are interfaces small?
[ ] Are retries centralized?
[ ] Are state transitions controlled?
[ ] Are errors typed?
[ ] Are tests included?
[ ] Is the design simpler than necessary alternatives?
[ ] Did the change introduce a new pattern unnecessarily?
```

---

# 173. Code Review Checklist

Human review should ask:

```text
Architecture
- Does the dependency direction remain correct?

SOLID
- Any SRP violation?
- Any OCP violation?
- Any LSP violation?
- Any oversized interface?
- Any dependency inversion violation?

Patterns
- Is every pattern justified?
- Could the implementation be simpler?

Reliability
- Can failure cause data loss?
- Is retry safe?
- Is processing idempotent?

AI
- Is AI treated as untrusted/probabilistic output?

UI
- Can any operation block the GUI?

Security
- Are secrets protected?

Testing
- Can the new code be tested without external services?
```

---

# 174. Final Principle

The most important rule is:

> **Architecture should make the correct implementation easy and the incorrect implementation difficult.**

For InsightFlow AI, that means:

```text
Gmail is behind an adapter.
AI is behind a provider interface.
Database is behind repositories.
Notifications are behind a provider.
Business logic is in the domain/application layers.
UI talks to use cases.
Long-running work is asynchronous.
State transitions are explicit.
Rules are data-driven.
AI output is validated.
```

The project should remain a **simple modular monolith with strong boundaries**, rather than becoming an over-engineered collection of patterns.

---

# 175. Final Design Pattern Philosophy

Use patterns to solve real problems.

Do not use patterns to make the code look architecturally sophisticated.

The target architecture is:

```text
Simple
+
Testable
+
Replaceable
+
Observable
+
Reliable
+
Extensible
```

not:

```text
Abstract
+
Complex
+
Over-engineered
```

This rule applies especially to AI coding agents, which must optimize for maintainability and correctness rather than maximizing abstraction.
