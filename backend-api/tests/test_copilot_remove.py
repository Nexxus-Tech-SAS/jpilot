from app.services.copilot_remove import (
    build_classic_vserver_removal_commands,
    build_lb_removal_commands,
    detect_lb_removal_request,
    parse_lb_removal_targets,
)


def test_parse_lb_removal_targets():
    message = "remove iis_lb_app and exchange_vs and all services and services groups link to it"
    assert parse_lb_removal_targets(message) == ["iis_lb_app", "exchange_vs"]


def test_detect_lb_removal_request():
    message = "remove iis_lb_app and exchange_vs and all services and services groups link to it"
    assert detect_lb_removal_request(message) is True
    assert detect_lb_removal_request("show lb vserver exchange_vs") is False


def test_build_classic_vserver_removal_commands():
    commands = build_classic_vserver_removal_commands(
        "exchange_vs",
        bound_service_groups=["exchange_sg"],
        service_groups=[
            {
                "name": "exchange_sg",
                "members": [
                    {"name": "192.168.20.234-8080", "ipAddress": "192.168.20.234", "port": 8080},
                    {"name": "192.168.20.234-8090", "ipAddress": "192.168.20.234", "port": 8090},
                ],
            }
        ],
        vip="192.168.20.224",
    )
    assert commands[0] == "unbind lb vserver exchange_vs -serviceGroupName exchange_sg"
    assert "rm lb vserver exchange_vs" in commands
    assert "unbind serviceGroup exchange_sg 192.168.20.234 8080" in commands
    assert "rm serviceGroup exchange_sg" in commands
    assert "rm ns ip 192.168.20.224" in commands


def test_build_lb_removal_commands_mixed_inventory():
    inventory = {
        "virtualServers": [
            {
                "name": "iis_lb_app",
                "source": "nextgen:application",
                "type": "nextgen",
            },
            {
                "name": "exchange_vs",
                "source": "nitro:lbvserver",
                "type": "classic",
                "servers": ["exchange_sg"],
                "virtualIp": "192.168.20.224",
            },
        ]
    }
    service_status = {
        "serviceGroups": [
            {
                "name": "exchange_sg",
                "members": [
                    {"name": "svc8080", "ipAddress": "192.168.20.234", "port": 8080},
                ],
            }
        ]
    }
    classic_commands, nextgen_apps = build_lb_removal_commands(
        ["iis_lb_app", "exchange_vs"],
        inventory,
        service_status,
    )
    assert nextgen_apps == ["iis_lb_app"]
    assert classic_commands[-1] == "save ns config"
    assert any("exchange_vs" in command for command in classic_commands)
