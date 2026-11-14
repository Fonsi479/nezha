# 三台低内存 VPS 的原生部署

上游主程序保持 v2.6.1，Agent 固定 v2.4.0，使用官方发行二进制，部署前核对 GitHub 发行资产的 SHA256。无需 Docker，不改变现有代理、流量计数或出站保护。

| 官方发行资产 | SHA256 |
| --- | --- |
| `nezhahq/nezha` v2.6.1 `dashboard-linux-amd64.zip` | `227a72efddf23a11cce0bce953c5733ca167728ea0c28af09e7a37c28f3ac9e4` |
| `nezhahq/agent` v2.4.0 `nezha-agent_linux_amd64.zip` | `0071f57e4dd42bd91adfdfb84291a1ebbc8b45c67f3511987e5982bea5eade7f` |

| 角色 | 配置 |
| --- | --- |
| 中心服务器 | Dashboard 与一个 Agent，主网卡 `eth0` |
| 两台云服务器 | 各运行一个 Agent，主网卡 `ens4` |
| 数据 | 根分区、CPU、内存、主网卡收发；30 天历史 |
| 访问 | 本机 SSH 转发至 `127.0.0.1:8008`，默认本机端口 `18765` |
| Agent 连接 | 中心服务器 TCP 8443，专用 CA 签发证书，校验证书与服务器地址 |

## 安装约束

1. 原生程序分别安装至 `/opt/nezha/dashboard/app` 和 `/opt/nezha/agent/nezha-agent`；数据保留在 `/opt/nezha/dashboard/data`。
2. 创建无登录权限的 `nezha` 系统用户，将配置复制至 `/etc/nezha/`。配置与密钥权限为 600，配置和数据目录为 700，所有者为 `nezha`。`/opt/nezha` 及程序目录为 755，二进制为 root 所有、755，确保服务用户能遍历目录并执行程序。
3. 按示例生成 Dashboard 和 Agent 配置，替换所有 `REPLACE_WITH_` 项。每台 Agent 使用不同 UUID；用户级 Agent 密钥只保存在私有配置中。
4. 专用 CA 的私钥离线保留。中心服务器持有服务器证书与私钥，三台 Agent 仅持有 CA 公共证书。证书 SAN 必须匹配 Agent 的 `server` 地址。
5. **先配置防火墙，再启动 Dashboard。** 中心服务器的 TCP 8008 必须拒绝一切非回环访问；TCP 8443 仅允许两台云服务器的源地址。IPv4、IPv6 均需检查。不要开放 8008 到公网；`listen_host` 同时作用于上游的 HTTP 和 HTTPS 监听。
6. 复制相应 systemd 单元，执行 `systemd-analyze verify`、`systemctl daemon-reload` 和 `systemctl enable --now`。首次启动仅通过 SSH 通道将默认管理员改为随机强密码，再接入 Agent。JWT 签名密钥通过权限为 600 的 `dashboard.env` 中 `NZ_JWTSECRETKEY` 注入。

Agent 仅采集监控：禁用命令、自动与强制更新、内网穿透和主动探测。主网卡白名单避免重复统计虚拟网卡；后续新增磁盘需调整分区白名单。

云服务器公网 IP 变化后，同步更新中心服务器的 8443 源地址白名单。中心地址变化后，还需重新签发匹配 SAN 的服务器证书并更新三台 Agent 的连接地址。证书到期前须续签并验证连接。

## 本机打开

双击仓库根目录的 `打开哪吒面板.command`。本机私有文件位于 `~/Library/Application Support/Codex/Nezha/`，包括 `access.json` 与登录凭据；这些文件不能提交到 Git。

`access.json` 格式：

```json
{
  "site_name": "我的 VPS",
  "local_port": 18765,
  "ssh_args": ["-i", "/absolute/path/to/private-key", "user@dashboard-host"],
  "ssh_env": {}
}
```

```sh
python3 deploy/three-vps/open_dashboard.py --no-open
```

## 流量口径

网络速率与累计流量分别显示。哪吒历史从接入开始，不能当成完整商家账单，也不导入或覆盖原 `vnStat`/旧面板数据库。GCP 两台机器沿用现有 UTC 自然月出站保护；面板中的周期流量也按 UTC 月界设置。未确认的套餐额度不填写。

GCP 出站保护触发后会阻断 Agent 的监控连接；中心面板会将其标为离线。监控不能绕过既有保护，恢复需按原流量保护规则处理。

## 验证与回滚

检查三台 Agent 在线、指标更新、网卡与根盘数值一致，历史指标非空，匿名读取服务器列表被拒绝，非允许来源不能访问 8008/8443，原代理和 GCP 流量保护仍运行。

停止新增服务可回滚：三台执行 `systemctl disable --now nezha-agent`，中心另执行 `systemctl disable --now nezha-dashboard`。保留数据和凭据便于恢复。仅删除本次带 `Nezha` 注释的防火墙规则，不重置防火墙。

Fork 的 GitHub Actions 保持禁用；变更仅做本地检查与真实部署验证。启用或运行 hosted CI 需另行授权预算。
