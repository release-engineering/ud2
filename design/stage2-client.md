# Stage 2: Align Client With Swagger Endpoints

## Objective

Refactor `ud2/client.py` so the public methods match the Unified Downloads API surface described in `reference/swagger.yaml`. Ensure request construction, routing, and response typing align with the new models delivered in Stage 1.

## Existing Structure

- `UDClient` currently exposes coarse-grained helpers (`create_product`, `list_products`, etc.) that point to placeholder REST paths such as `product` and `version`.
- `_request` centralizes HTTP interactions and already handles Pydantic payload serialization and response coercion.
- `coerce_model` converts JSON into Pydantic classes when given a `model` argument.

## Endpoint Mapping

| API Path | Method | Current Helper (rename if needed) | Expected URL | Response Model |
| --- | --- | --- | --- | --- |
| `/products` | GET | `list_products` | `GET /products` | `controllers.ProductPaginatedResponse` (define a pagination model or return `Dict[str, Any]`) |
| `/products` | POST | `create_product` | `POST /products` | `Product` |
| `/products/{id}` | GET | `get_product` (new) | `GET /products/{id}` | `Product` |
| `/products/{id}` | PUT | `update_product` | `PUT /products/{id}` | `Product` |
| `/products/{id}` | DELETE | `delete_product` | `DELETE /products/{id}` | `None` |
| `/products/{id}/product_versions` | GET | `list_product_versions` | `GET /products/{id}/product_versions` | `List[Version]` |
| `/products/{id}/product_versions` | POST | `create_product_version` | `POST /products/{id}/product_versions` | `Version` |
| `/products/{id}/product_versions/{version_id}` | GET | `get_product_version` | `GET /products/{id}/product_versions/{version_id}` | `Version` |
| `/products/{id}/product_versions/{version_id}` | PUT | `update_product_version` | `PUT /products/{id}/product_versions/{version_id}` | `Version` |
| `/products/{id}/product_versions/{version_id}` | DELETE | `delete_product_version` | `DELETE /products/{id}/product_versions/{version_id}` | `None` |
| `/product_versions/{product_version_id}/repositories` | GET | `list_repositories` | `GET /product_versions/{product_version_id}/repositories` | `controllers.RepositoryPaginatedResponse` or custom pagination model |
| `/product_versions/{product_version_id}/repositories` | POST | `create_repository` | `POST /product_versions/{product_version_id}/repositories` | `Repository` |
| `/product_versions/{product_version_id}/repositories/{id}` | GET | `get_repository` | `GET /product_versions/{product_version_id}/repositories/{id}` | `Repository` |
| `/product_versions/{product_version_id}/repositories/{id}` | PUT | `update_repository` | `PUT /product_versions/{product_version_id}/repositories/{id}` | `Repository` |
| `/product_versions/{product_version_id}/repositories/{id}` | DELETE | `delete_repository` | `DELETE /product_versions/{product_version_id}/repositories/{id}` | `None` |

## Implementation Guidelines

1. **Normalize URL construction**
   - Rename the `_request` parameter `resource` to `path` to avoid ambiguity.
   - Accept a complete path string (already beginning with `/`) to reduce manual string concatenation logic inside helpers.
   - Ensure `_request` joins `self._base_url` with the provided path using `f"{self._base_url}{path}"`.

2. **Parameter Handling**
   - Represent path variables explicitly in helper signatures (e.g., `def get_product(self, product_id: int) -> Product`).
   - Keep query params optional dictionaries but document supported keys (e.g., `page`, `limit`, `sort`).
   - For repository endpoints, require the parent `product_version_id`.

3. **Response Typing**
   - Pass `model` arguments into `_request` so `coerce_model` returns typed objects or lists.
   - Introduce pagination Pydantic models if Stage 1 delivers them; otherwise return raw dictionaries.
   - For deletion endpoints, return `None` and rely on `response.raise_for_status()` for success and error propagation.

4. **Error Handling**
   - Continue to rely on `requests` exceptions for HTTP errors; document expected status codes in method docstrings.
   - Consider raising custom exceptions only if later stages require tailored CLI messaging (not in scope here).

5. **Testing Hooks**
   - Maintain optional `session` injection on the client to facilitate unit testing with mocked sessions.
   - Add unit tests (outside this design) that assert URL correctness, payload serialization with aliases, and model coercion.

## Deliverables

- Updated helper methods in `ud2/client.py` matching swagger endpoints.
- Additional helper methods such as `get_product`, `get_repository`, etc., covering all GET operations.
- Comprehensive docstrings describing required parameters, query options, and response models.
- No CLI changes yet.

## Open Questions

- Decide whether to introduce generic pagination models (`PaginatedProducts`, `PaginatedRepositories`) or to deserialize into existing controllers.* shapes.
- Confirm if search endpoints (`/product/search`) still exist; consider removing legacy helpers if they are no longer supported.

<!-- The end. -->
