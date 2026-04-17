# Kubernetes Troubleshooting

## Pod Inspection

```bash
# Get pods with details
kubectl get pods -n production -o wide
kubectl get pods --field-selector status.phase!=Running -n production

# Describe pod (shows events, conditions, resource usage)
kubectl describe pod <pod-name> -n production

# Pod logs
kubectl logs <pod-name> -n production
kubectl logs <pod-name> -n production --previous        # crashed container
kubectl logs <pod-name> -n production -c <container>     # specific container
kubectl logs <pod-name> -n production -f                 # follow
kubectl logs <pod-name> -n production --since=1h         # time-based
kubectl logs deployment/web-app -n production --all-containers=true

# Execute commands in pod
kubectl exec -it <pod-name> -n production -- /bin/sh
kubectl exec <pod-name> -n production -- env
kubectl exec <pod-name> -n production -- cat /etc/config/app.yaml

# Port forward
kubectl port-forward <pod-name> 8080:8080 -n production
kubectl port-forward service/web-app 8080:80 -n production
```

## Deployment Debugging

```bash
# Rollout status and history
kubectl rollout status deployment/web-app -n production
kubectl rollout history deployment/web-app -n production

# ReplicaSets
kubectl get rs -n production
kubectl describe rs <rs-name> -n production

# Rollback
kubectl rollout undo deployment/web-app -n production
kubectl rollout undo deployment/web-app --to-revision=2 -n production

# Restart (recreate all pods)
kubectl rollout restart deployment/web-app -n production
```

## Network Debugging

```bash
# Services and endpoints
kubectl get svc -n production
kubectl get endpoints web-app -n production
kubectl describe svc web-app -n production

# Ingress
kubectl get ingress -n production
kubectl describe ingress web-app -n production

# NetworkPolicies
kubectl get networkpolicy -n production
kubectl describe networkpolicy <name> -n production

# DNS resolution test
kubectl run dns-test --image=busybox:1.36 --rm -it --restart=Never -- \
  nslookup web-app.production.svc.cluster.local

# Connectivity test
kubectl run curl-test --image=curlimages/curl --rm -it --restart=Never -- \
  curl -v http://web-app.production.svc.cluster.local:8080/health
```

## Resource and Configuration

```bash
# Events (sorted by time)
kubectl get events -n production --sort-by='.lastTimestamp'

# Resource usage
kubectl top pods -n production
kubectl top nodes

# ConfigMaps and Secrets
kubectl get configmap app-config -n production -o yaml
kubectl get secret app-secrets -n production -o jsonpath='{.data.password}' | base64 -d

# PVC status
kubectl get pvc -n production
kubectl describe pvc database-pvc -n production

# RBAC audit
kubectl auth can-i --list --as=system:serviceaccount:production:my-app-sa
```

## Debug Containers

```bash
# Ephemeral debug container on running pod
kubectl debug -it <pod-name> -n production \
  --image=nicolaka/netshoot:latest \
  --target=<container-name>

# Copy pod with debug tools
kubectl debug <pod-name> -n production \
  -it --image=ubuntu:latest \
  --share-processes --copy-to=debug-pod

# Debug on a node
kubectl debug node/<node-name> -it --image=ubuntu:latest
```

## Common Issues

### Pod Pending

| Cause                    | Diagnosis                                                   |
| ------------------------ | ----------------------------------------------------------- |
| Insufficient resources   | `kubectl describe pod` — check Events for FailedScheduling  |
| PVC not bound            | `kubectl get pvc` — check status                            |
| Node selector mismatch   | `kubectl get pod -o yaml` — check nodeSelector/affinity     |
| Image pull failure       | `kubectl describe pod` — check Events for ImagePullBackOff  |

### CrashLoopBackOff

```bash
# Check previous container logs
kubectl logs <pod-name> -n production --previous

# Check if liveness probe is killing the container
kubectl describe pod <pod-name> | grep -A 10 "Liveness"

# Check OOMKill (resource limits too low)
kubectl describe pod <pod-name> | grep -i "oom\|kill\|memory"

# Debug with shell override
kubectl run debug --image=myapp:v1.0.0 -it --rm --restart=Never -- /bin/sh
```

### ImagePullBackOff

```bash
# Verify image exists
kubectl describe pod <pod-name> | grep -A 5 "Image"

# Check registry credentials
kubectl get secret registry-credentials -n production -o yaml

# Test pull manually
kubectl run test --image=myregistry.io/myapp:v1.0.0 --restart=Never
```

### Service Not Reachable

```bash
# Verify endpoints exist
kubectl get endpoints <service-name> -n production

# Check selector matches pod labels
kubectl get svc <service-name> -n production -o yaml | grep -A 5 selector
kubectl get pods -n production --show-labels

# Check NetworkPolicy blocking traffic
kubectl get networkpolicy -n production
```

### Node Issues

```bash
# Node status and conditions
kubectl get nodes
kubectl describe node <node-name>

# Check node resource pressure
kubectl describe node <node-name> | grep -A 10 "Conditions"

# Cordon/drain for maintenance
kubectl cordon <node-name>
kubectl drain <node-name> --ignore-daemonsets --delete-emptydir-data
```
