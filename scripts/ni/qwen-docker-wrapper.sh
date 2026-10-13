#!/bin/bash
set -euo pipefail

args=("$@")
workspace_source=""
if [[ -n "${SANDBOX_FLAGS:-}" ]]; then
  read -r -a sandbox_flags <<<"$SANDBOX_FLAGS"
  for ((i = 0; i < ${#sandbox_flags[@]}; i++)); do
    case "${sandbox_flags[i]}" in
      --volume|-v)
        spec="${sandbox_flags[i + 1]:-}"
        source="${spec%%:*}"
        target="${spec#*:}"
        target="${target%%:*}"
        if [[ "$target" == "/app" ]]; then
          workspace_source="$source"
          break
        fi
        ;;
    esac
  done
fi

if [[ -n "${QWEN_SANDBOX_NETWORK_NAME:-}" ]]; then
  proxy_network="${QWEN_SANDBOX_NETWORK_NAME}-proxy"
  for ((i = 0; i < ${#args[@]}; i++)); do
    case "${args[i]}" in
      --network|-n)
        if [[ "${args[i + 1]:-}" == "qwen-code-sandbox" ]]; then
          args[i + 1]="$QWEN_SANDBOX_NETWORK_NAME"
        elif [[ "${args[i + 1]:-}" == "qwen-code-sandbox-proxy" ]]; then
          args[i + 1]="${QWEN_SANDBOX_NETWORK_NAME}-proxy"
        fi
        ;;
      network)
        case "${args[i + 1]:-}" in
          inspect|create|rm)
            j=$((${#args[@]} - 1))
            if [[ "${args[j]}" == "qwen-code-sandbox" ]]; then
              args[j]="$QWEN_SANDBOX_NETWORK_NAME"
            elif [[ "${args[j]}" == "qwen-code-sandbox-proxy" ]]; then
              args[j]="$proxy_network"
            fi
            ;;
          connect|disconnect)
            if [[ "${args[i + 2]:-}" == "qwen-code-sandbox" ]]; then
              args[i + 2]="$QWEN_SANDBOX_NETWORK_NAME"
            fi
            if [[ "${args[i + 3]:-}" == "qwen-code-sandbox-proxy" ]]; then
              args[i + 3]="$proxy_network"
            fi
            ;;
        esac
        ;;
      --name)
        if [[ "${args[i + 1]:-}" == "qwen-code-sandbox-proxy" ]]; then
          args[i + 1]="$proxy_network"
        fi
        ;;
      qwen-code-sandbox-proxy)
        args[i]="$proxy_network"
        ;;
    esac
  done

  # Qwen passes this fixed proxy hostname into the sandbox environment.
  # Keep it as a network-scoped alias even though each trial has a unique
  # proxy container name.
  if [[ "${args[0]:-}" == "network" && "${args[1]:-}" == "connect" \
        && "${args[2]:-}" == "$QWEN_SANDBOX_NETWORK_NAME" \
        && "${args[3]:-}" == "$proxy_network" ]]; then
    args=(network connect --alias qwen-code-sandbox-proxy "${args[@]:2}")
  fi

  # The proxy is reached over a private per-trial Docker network; host publishing
  # is unnecessary because the outer trial has a local readiness forwarder.
  for ((i = 0; i < ${#args[@]}; i++)); do
    if [[ "${args[i]}" == "-p" && "${args[i + 1]:-}" == "8877:8877" ]]; then
      unset 'args[i]' 'args[i+1]'
      args=("${args[@]}")
      break
    fi
  done
fi

# In the nested-Docker benchmark runner, Qwen's native proxy readiness probe runs
# in the outer trial container, while the proxy itself runs in a Docker sidecar.
# Give that trial a local-only forwarder to its uniquely named proxy network.
if [[ "${args[0]:-}" == "network" && "${args[1]:-}" =~ ^(inspect|create)$ \
      && "${args[${#args[@]}-1]:-}" == "${QWEN_SANDBOX_NETWORK_NAME:-}-proxy" \
      && -n "${QWEN_AGENT_CONTAINER_NAME:-}" ]]; then
  /usr/bin/docker "${args[@]}"
  rc=$?
  if [[ $rc -eq 0 ]]; then
    /usr/bin/docker network connect "${QWEN_SANDBOX_NETWORK_NAME}-proxy" \
      "$QWEN_AGENT_CONTAINER_NAME" >/dev/null 2>&1 || true
    node -e 'const n=require("node:net");n.createServer(c=>{const x=n.connect(8877,process.env.QWEN_SANDBOX_NETWORK_NAME+"-proxy",()=>c.pipe(x).pipe(c));x.on("error",()=>c.destroy());c.on("error",()=>x.destroy())}).listen(8877,"127.0.0.1")' \
      </dev/null >/dev/null 2>&1 &
  fi
  exit "$rc"
fi

if [[ -n "$workspace_source" ]]; then
  for ((i = 0; i < ${#args[@]}; i++)); do
    case "${args[i]}" in
      --volume|-v)
        spec="${args[i + 1]:-}"
        source="${spec%%:*}"
        if [[ "$source" == "/app" || "$source" == /app/* ]]; then
          args[i + 1]="${workspace_source}${source#/app}:${spec#*:}"
        fi
        ;;
    esac
  done
fi

is_sandbox_run=false
if [[ "${args[0]:-}" == "run" ]]; then
  for arg in "${args[@]}"; do
    if [[ "$arg" == "${QWEN_SANDBOX_IMAGE:-__unset__}" ]]; then
      is_sandbox_run=true
      break
    fi
  done
fi
if [[ "$is_sandbox_run" == true ]]; then
  has_name=false
  for ((i = 0; i < ${#args[@]}; i++)); do
    if [[ "${args[i]}" == "--name" ]]; then
      has_name=true
      if [[ "${args[i + 1]:-}" != "${QWEN_SANDBOX_NETWORK_NAME:-}-proxy" ]]; then
        args[i + 1]="${QWEN_AGENT_CONTAINER_NAME}-sandbox"
      fi
    fi
  done
  if [[ "$has_name" == false ]]; then
    args=("${args[0]}" --name "${QWEN_AGENT_CONTAINER_NAME}-sandbox" "${args[@]:1}")
  fi
  args=(
    "${args[0]}"
    --env QWEN_HOME=/app/.qwen-home
    "${args[@]:1}"
  )
fi


exec /usr/bin/docker "${args[@]}"
