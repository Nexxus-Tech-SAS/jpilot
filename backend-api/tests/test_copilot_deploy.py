import json

from app.schemas.copilot import ToolCallTrace
from app.services.copilot_deploy import (
    build_classic_lb_commands,
    detect_classic_lb_form_submission,
    detect_natural_language_lb_request,
    detect_nextgen_application_form_submission,
    format_create_application_response,
    parse_backend_servers,
    parse_classic_lb_form_fields,
    parse_configuration_form_fields,
    parse_natural_language_lb_request,
)
from app.services.copilot_orchestration import deployment_write_complete
from app.services.copilot_orchestrator import _deployment_may_be_incomplete


_FORM = """Configuration inputs for: Create IIS Load Balancer
- Application Name: iis_lb_app
- Virtual IP (VIP): 192.168.20.227
- Port: 80
- Protocol: HTTP
- Backend IIS Server IPs: 192.168.21.227, 192.168.21.228, 192.168.21.229
- Load Balancing Method: LEASTCONNECTION

Proceed with the configuration on the connected appliance using these values."""

_STOREFRONT_FORM = """Configuration inputs for: StoreFront Load Balancer Configuration
- Application Name: storefront_lb
- VIP Address: 192.168.21.230
- Protocol: SSL_BRIDGE
- VIP Port: 443
- Backend StoreFront Server IPs (comma-separated): 192.168.21.231, 192.168.21.232
- Backend Server Port: 443
- Load Balancing Algorithm: LEASTCONNECTION

Proceed with the configuration on the connected appliance using these values."""


def test_parse_nextgen_form_fields():
    fields = parse_configuration_form_fields(_FORM)
    assert fields["name"] == "iis_lb_app"
    assert fields["virtual_ip"] == "192.168.20.227"
    assert fields["port"] == "80"
    assert fields["protocol"] == "HTTP"
    assert "192.168.21.227" in fields["servers"]


def test_parse_backend_servers():
    assert parse_backend_servers("10.0.0.1, 10.0.0.2") == ["10.0.0.1", "10.0.0.2"]


def test_detect_nextgen_application_form_submission():
    assert detect_nextgen_application_form_submission(_FORM) is True
    assert detect_nextgen_application_form_submission(_STOREFRONT_FORM) is True


def test_parse_storefront_form_fields():
    fields = parse_configuration_form_fields(_STOREFRONT_FORM)
    assert fields["name"] == "storefront_lb"
    assert fields["virtual_ip"] == "192.168.21.230"
    assert fields["port"] == "443"
    assert fields["servers_port"] == "443"
    assert fields["protocol"] == "SSL_BRIDGE"
    assert "192.168.21.231" in fields["servers"]


def test_classic_lb_form_submission_not_nextgen():
    classic = """Configuration inputs for: Load balancer — Application
- Virtual server name: lb_app_01
- VIP address: 10.0.0.10
- Backend IP addresses (comma-separated): 10.0.0.1
"""
    assert detect_nextgen_application_form_submission(classic) is False


def test_format_create_application_response():
    text = format_create_application_response(
        "Martica",
        {
            "application": {
                "name": "iis_lb_app",
                "virtual_ip": "192.168.20.227",
                "port": 80,
                "protocol": "HTTP",
                "servers": ["192.168.21.227"],
            }
        },
    )
    assert "created via Next-Gen API" in text
    assert "iis_lb_app" in text


def test_nextgen_create_marks_deployment_complete():
    traces = [
        ToolCallTrace(
            name="netscaler_create_application",
            arguments={"name": "iis_lb_app"},
            result=json.dumps({"success": True, "application": {"name": "iis_lb_app"}}),
        )
    ]
    assert deployment_write_complete(traces) is True
    assert _deployment_may_be_incomplete(traces, _FORM, "operator") is False


_EXCHANGE_FORM = """Configuration inputs for: Exchange Load Balancer Configuration
- LB vServer name: exchange_vs
- Service Group name: exchange_sg
- SSL Certificate to bind: wildcard-cert
- Front-end (VIP) port: 443
- Backend server IP: 192.168.20.234
- Backend port 1: 8080
- Backend port 2: 8090
- Load Balancing method: LEASTCONNECTION
- Health monitor: ping

Proceed with the configuration on the connected appliance using these values. Do not ask the same questions in prose again."""


def test_detect_classic_lb_form_submission_exchange():
    assert detect_nextgen_application_form_submission(_EXCHANGE_FORM) is False
    assert detect_classic_lb_form_submission(_EXCHANGE_FORM) is False


def test_parse_classic_lb_form_with_vip():
    form = _EXCHANGE_FORM.replace(
        "- Front-end (VIP) port: 443",
        "- VIP address: 192.168.20.224\n- Front-end (VIP) port: 443",
    )
    fields = parse_classic_lb_form_fields(form)
    assert fields["vserver_name"] == "exchange_vs"
    assert fields["service_group"] == "exchange_sg"
    assert fields["vip"] == "192.168.20.224"
    assert fields["backend_ports"] == [8080, 8090]
    assert detect_classic_lb_form_submission(form) is True


def test_build_classic_lb_commands_exchange():
    fields = {
        "vserver_name": "exchange_vs",
        "service_group": "exchange_sg",
        "vip": "192.168.20.224",
        "frontend_port": 443,
        "backend_ip": "192.168.20.234",
        "backend_ports": [8080, 8090],
        "lb_method": "LEASTCONNECTION",
        "monitor": "ping",
        "ssl_cert": "wildcard-cert",
        "backend_protocol": "HTTP",
    }
    commands = build_classic_lb_commands(fields)
    assert commands[0] == "add ns ip 192.168.20.224 255.255.255.255 -type VIP"
    assert "add serviceGroup exchange_sg HTTP" in commands
    assert "bind serviceGroup exchange_sg 192.168.20.234 8080" in commands
    assert "bind serviceGroup exchange_sg 192.168.20.234 8090" in commands
    assert "bind lb vserver exchange_vs exchange_sg" in commands
    assert "bind ssl vserver exchange_vs -certkeyName wildcard-cert" in commands
    assert commands[-1] == "save ns config"


_DEMO1_MESSAGE = (
    "Create a load balancer for demo1. Front end ip 192.168.20.224 SSL "
    "(use the wildcard certificate). Backend servers 192.168.20.234 ports 8060 and 8070. "
    "TCP monitor, no persistence."
)


def test_parse_natural_language_lb_demo1():
    fields = parse_natural_language_lb_request(_DEMO1_MESSAGE)
    assert fields["vserver_name"] == "demo1_vs"
    assert fields["vip"] == "192.168.20.224"
    assert fields["backend_ip"] == "192.168.20.234"
    assert fields["backend_ports"] == [8060, 8070]
    assert fields["ssl_cert"] == "wildcard-cert"
    assert fields["monitor"] == "tcp"
    assert fields["backend_protocol"] == "TCP"
    assert fields["persistence"] == "NONE"
    assert detect_natural_language_lb_request(_DEMO1_MESSAGE, fields) is True


def test_build_classic_lb_commands_demo1():
    fields = parse_natural_language_lb_request(_DEMO1_MESSAGE)
    assert fields["vserver_protocol"] == "SSL_TCP"
    assert fields["monitor"] == "tcp"
    commands = build_classic_lb_commands(fields, skip_vip_add=True)
    assert "add serviceGroup demo1_sg TCP" in commands
    assert "bind serviceGroup demo1_sg 192.168.20.234 8060" in commands
    assert "bind serviceGroup demo1_sg -monitorName tcp" in commands
    vserver_line = next(command for command in commands if command.startswith("add lb vserver demo1_vs"))
    assert "SSL_TCP" in vserver_line
    assert "-persistenceType NONE" in vserver_line
    assert "bind ssl vserver demo1_vs -certkeyName wildcard-cert" in commands
