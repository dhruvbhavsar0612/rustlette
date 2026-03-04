"""Tests for rustlette.status — HTTP and WebSocket status codes."""

import warnings

import pytest

from rustlette import status


class TestHTTPStatusCodes:
    """Verify all HTTP status code constants exist and have correct values."""

    # 1xx Informational
    def test_100_continue(self):
        assert status.HTTP_100_CONTINUE == 100

    def test_101_switching_protocols(self):
        assert status.HTTP_101_SWITCHING_PROTOCOLS == 101

    def test_102_processing(self):
        assert status.HTTP_102_PROCESSING == 102

    def test_103_early_hints(self):
        assert status.HTTP_103_EARLY_HINTS == 103

    # 2xx Success
    def test_200_ok(self):
        assert status.HTTP_200_OK == 200

    def test_201_created(self):
        assert status.HTTP_201_CREATED == 201

    def test_202_accepted(self):
        assert status.HTTP_202_ACCEPTED == 202

    def test_203_non_authoritative(self):
        assert status.HTTP_203_NON_AUTHORITATIVE_INFORMATION == 203

    def test_204_no_content(self):
        assert status.HTTP_204_NO_CONTENT == 204

    def test_205_reset_content(self):
        assert status.HTTP_205_RESET_CONTENT == 205

    def test_206_partial_content(self):
        assert status.HTTP_206_PARTIAL_CONTENT == 206

    def test_207_multi_status(self):
        assert status.HTTP_207_MULTI_STATUS == 207

    def test_208_already_reported(self):
        assert status.HTTP_208_ALREADY_REPORTED == 208

    def test_226_im_used(self):
        assert status.HTTP_226_IM_USED == 226

    # 3xx Redirection
    def test_300_multiple_choices(self):
        assert status.HTTP_300_MULTIPLE_CHOICES == 300

    def test_301_moved_permanently(self):
        assert status.HTTP_301_MOVED_PERMANENTLY == 301

    def test_302_found(self):
        assert status.HTTP_302_FOUND == 302

    def test_303_see_other(self):
        assert status.HTTP_303_SEE_OTHER == 303

    def test_304_not_modified(self):
        assert status.HTTP_304_NOT_MODIFIED == 304

    def test_305_use_proxy(self):
        assert status.HTTP_305_USE_PROXY == 305

    def test_306_reserved(self):
        assert status.HTTP_306_RESERVED == 306

    def test_307_temporary_redirect(self):
        assert status.HTTP_307_TEMPORARY_REDIRECT == 307

    def test_308_permanent_redirect(self):
        assert status.HTTP_308_PERMANENT_REDIRECT == 308

    # 4xx Client Error
    def test_400_bad_request(self):
        assert status.HTTP_400_BAD_REQUEST == 400

    def test_401_unauthorized(self):
        assert status.HTTP_401_UNAUTHORIZED == 401

    def test_402_payment_required(self):
        assert status.HTTP_402_PAYMENT_REQUIRED == 402

    def test_403_forbidden(self):
        assert status.HTTP_403_FORBIDDEN == 403

    def test_404_not_found(self):
        assert status.HTTP_404_NOT_FOUND == 404

    def test_405_method_not_allowed(self):
        assert status.HTTP_405_METHOD_NOT_ALLOWED == 405

    def test_406_not_acceptable(self):
        assert status.HTTP_406_NOT_ACCEPTABLE == 406

    def test_407_proxy_auth_required(self):
        assert status.HTTP_407_PROXY_AUTHENTICATION_REQUIRED == 407

    def test_408_request_timeout(self):
        assert status.HTTP_408_REQUEST_TIMEOUT == 408

    def test_409_conflict(self):
        assert status.HTTP_409_CONFLICT == 409

    def test_410_gone(self):
        assert status.HTTP_410_GONE == 410

    def test_411_length_required(self):
        assert status.HTTP_411_LENGTH_REQUIRED == 411

    def test_412_precondition_failed(self):
        assert status.HTTP_412_PRECONDITION_FAILED == 412

    def test_413_content_too_large(self):
        assert status.HTTP_413_CONTENT_TOO_LARGE == 413

    def test_414_uri_too_long(self):
        assert status.HTTP_414_URI_TOO_LONG == 414

    def test_415_unsupported_media_type(self):
        assert status.HTTP_415_UNSUPPORTED_MEDIA_TYPE == 415

    def test_416_range_not_satisfiable(self):
        assert status.HTTP_416_RANGE_NOT_SATISFIABLE == 416

    def test_417_expectation_failed(self):
        assert status.HTTP_417_EXPECTATION_FAILED == 417

    def test_418_im_a_teapot(self):
        assert status.HTTP_418_IM_A_TEAPOT == 418

    def test_421_misdirected_request(self):
        assert status.HTTP_421_MISDIRECTED_REQUEST == 421

    def test_422_unprocessable_content(self):
        assert status.HTTP_422_UNPROCESSABLE_CONTENT == 422

    def test_423_locked(self):
        assert status.HTTP_423_LOCKED == 423

    def test_424_failed_dependency(self):
        assert status.HTTP_424_FAILED_DEPENDENCY == 424

    def test_425_too_early(self):
        assert status.HTTP_425_TOO_EARLY == 425

    def test_426_upgrade_required(self):
        assert status.HTTP_426_UPGRADE_REQUIRED == 426

    def test_428_precondition_required(self):
        assert status.HTTP_428_PRECONDITION_REQUIRED == 428

    def test_429_too_many_requests(self):
        assert status.HTTP_429_TOO_MANY_REQUESTS == 429

    def test_431_request_header_fields_too_large(self):
        assert status.HTTP_431_REQUEST_HEADER_FIELDS_TOO_LARGE == 431

    def test_451_unavailable_for_legal_reasons(self):
        assert status.HTTP_451_UNAVAILABLE_FOR_LEGAL_REASONS == 451

    # 5xx Server Error
    def test_500_internal_server_error(self):
        assert status.HTTP_500_INTERNAL_SERVER_ERROR == 500

    def test_501_not_implemented(self):
        assert status.HTTP_501_NOT_IMPLEMENTED == 501

    def test_502_bad_gateway(self):
        assert status.HTTP_502_BAD_GATEWAY == 502

    def test_503_service_unavailable(self):
        assert status.HTTP_503_SERVICE_UNAVAILABLE == 503

    def test_504_gateway_timeout(self):
        assert status.HTTP_504_GATEWAY_TIMEOUT == 504

    def test_505_http_version_not_supported(self):
        assert status.HTTP_505_HTTP_VERSION_NOT_SUPPORTED == 505

    def test_506_variant_also_negotiates(self):
        assert status.HTTP_506_VARIANT_ALSO_NEGOTIATES == 506

    def test_507_insufficient_storage(self):
        assert status.HTTP_507_INSUFFICIENT_STORAGE == 507

    def test_508_loop_detected(self):
        assert status.HTTP_508_LOOP_DETECTED == 508

    def test_510_not_extended(self):
        assert status.HTTP_510_NOT_EXTENDED == 510

    def test_511_network_auth_required(self):
        assert status.HTTP_511_NETWORK_AUTHENTICATION_REQUIRED == 511


class TestWebSocketStatusCodes:
    """Verify all WebSocket close code constants."""

    def test_1000_normal_closure(self):
        assert status.WS_1000_NORMAL_CLOSURE == 1000

    def test_1001_going_away(self):
        assert status.WS_1001_GOING_AWAY == 1001

    def test_1002_protocol_error(self):
        assert status.WS_1002_PROTOCOL_ERROR == 1002

    def test_1003_unsupported_data(self):
        assert status.WS_1003_UNSUPPORTED_DATA == 1003

    def test_1005_no_status_rcvd(self):
        assert status.WS_1005_NO_STATUS_RCVD == 1005

    def test_1006_abnormal_closure(self):
        assert status.WS_1006_ABNORMAL_CLOSURE == 1006

    def test_1007_invalid_frame_payload_data(self):
        assert status.WS_1007_INVALID_FRAME_PAYLOAD_DATA == 1007

    def test_1008_policy_violation(self):
        assert status.WS_1008_POLICY_VIOLATION == 1008

    def test_1009_message_too_big(self):
        assert status.WS_1009_MESSAGE_TOO_BIG == 1009

    def test_1010_mandatory_ext(self):
        assert status.WS_1010_MANDATORY_EXT == 1010

    def test_1011_internal_error(self):
        assert status.WS_1011_INTERNAL_ERROR == 1011

    def test_1012_service_restart(self):
        assert status.WS_1012_SERVICE_RESTART == 1012

    def test_1013_try_again_later(self):
        assert status.WS_1013_TRY_AGAIN_LATER == 1013

    def test_1014_bad_gateway(self):
        assert status.WS_1014_BAD_GATEWAY == 1014

    def test_1015_tls_handshake(self):
        assert status.WS_1015_TLS_HANDSHAKE == 1015


class TestDeprecatedAliases:
    """Deprecated HTTP status names must still work but emit DeprecationWarning."""

    def test_413_request_entity_too_large_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            val = status.HTTP_413_REQUEST_ENTITY_TOO_LARGE
            assert val == 413
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "HTTP_413_CONTENT_TOO_LARGE" in str(w[0].message)

    def test_414_request_uri_too_long_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            val = status.HTTP_414_REQUEST_URI_TOO_LONG
            assert val == 414
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_416_requested_range_not_satisfiable_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            val = status.HTTP_416_REQUESTED_RANGE_NOT_SATISFIABLE
            assert val == 416
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_422_unprocessable_entity_deprecated(self):
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            val = status.HTTP_422_UNPROCESSABLE_ENTITY
            assert val == 422
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)

    def test_unknown_attribute_raises_error(self):
        with pytest.raises(AttributeError):
            _ = status.HTTP_999_DOES_NOT_EXIST


class TestModuleExports:
    """Verify __all__ contains all expected names."""

    def test_all_contains_http_codes(self):
        for name in status.__all__:
            assert hasattr(status, name), f"Missing: {name}"

    def test_all_count(self):
        # 63 HTTP + 15 WS = 78 total
        assert len(status.__all__) == 78
