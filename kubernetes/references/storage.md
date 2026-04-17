# Kubernetes Storage

## StorageClass

### AWS EBS (gp3)

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd
  annotations:
    storageclass.kubernetes.io/is-default-class: "true"
provisioner: ebs.csi.aws.com
parameters:
  type: gp3
  iops: "3000"
  throughput: "125"
  encrypted: "true"
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
reclaimPolicy: Delete
```

### GCE Persistent Disk (SSD)

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd-gce
provisioner: pd.csi.storage.gke.io
parameters:
  type: pd-ssd
  replication-type: regional-pd
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

### Azure Disk (Premium SSD)

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: fast-ssd-azure
provisioner: disk.csi.azure.com
parameters:
  storageaccounttype: Premium_LRS
  kind: Managed
volumeBindingMode: WaitForFirstConsumer
allowVolumeExpansion: true
```

## PersistentVolumeClaim

### Dynamic Provisioning

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-pvc
  namespace: production
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: fast-ssd
  resources:
    requests:
      storage: 50Gi
```

### Shared Storage (ReadWriteMany)

```yaml
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: shared-assets
  namespace: production
spec:
  accessModes: ["ReadWriteMany"]
  storageClassName: nfs-storage
  resources:
    requests:
      storage: 100Gi
```

## Mounting in Pods

```yaml
spec:
  containers:
    - name: app
      volumeMounts:
        - name: data
          mountPath: /var/lib/app
        - name: cache
          mountPath: /cache
  volumes:
    - name: data
      persistentVolumeClaim:
        claimName: database-pvc
    - name: cache
      emptyDir:
        sizeLimit: 1Gi
```

## StatefulSet VolumeClaimTemplates

```yaml
volumeClaimTemplates:
  - metadata:
      name: data
    spec:
      accessModes: ["ReadWriteOnce"]
      storageClassName: fast-ssd
      resources:
        requests:
          storage: 50Gi
```

## Volume Snapshots

```yaml
apiVersion: snapshot.storage.k8s.io/v1
kind: VolumeSnapshot
metadata:
  name: database-snapshot
  namespace: production
spec:
  volumeSnapshotClassName: csi-snapclass
  source:
    persistentVolumeClaimName: database-pvc
---
# Restore from snapshot
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: database-restored
  namespace: production
spec:
  accessModes: ["ReadWriteOnce"]
  storageClassName: fast-ssd
  dataSource:
    name: database-snapshot
    kind: VolumeSnapshot
    apiGroup: snapshot.storage.k8s.io
  resources:
    requests:
      storage: 50Gi
```

## Volume Expansion

Requires `allowVolumeExpansion: true` on the StorageClass. Update the PVC `spec.resources.requests`
to the new size — Kubernetes handles the rest.

## EmptyDir Volumes

```yaml
volumes:
  # Memory-backed (fast, limited by node memory)
  - name: cache
    emptyDir:
      medium: Memory
      sizeLimit: 1Gi
  # Disk-backed (default)
  - name: scratch
    emptyDir:
      sizeLimit: 10Gi
```

## Projected Volumes

Combine multiple sources into one mount:

```yaml
volumes:
  - name: combined
    projected:
      sources:
        - secret:
            name: app-secrets
            items:
              - key: password
                path: secrets/password
        - configMap:
            name: app-config
            items:
              - key: config.yaml
                path: config/app.yaml
        - downwardAPI:
            items:
              - path: pod/labels
                fieldRef:
                  fieldPath: metadata.labels
```

## Best Practices

1. **Dynamic provisioning** — use StorageClasses, avoid static PV creation
2. **WaitForFirstConsumer** — bind volumes in the same zone as the pod
3. **Volume expansion** — always enable `allowVolumeExpansion`
4. **Snapshots** — regular snapshots for backup and recovery
5. **Access modes** — ReadWriteOnce for single-pod, ReadWriteMany for shared
6. **Encryption** — enable at-rest encryption via StorageClass parameters
7. **Size planning** — start conservatively, expand as needed
