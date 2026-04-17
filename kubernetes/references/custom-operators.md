# Custom Operators

## CustomResourceDefinition (CRD)

```yaml
apiVersion: apiextensions.k8s.io/v1
kind: CustomResourceDefinition
metadata:
  name: databases.mycompany.io
spec:
  group: mycompany.io
  names:
    kind: Database
    listKind: DatabaseList
    plural: databases
    singular: database
    shortNames:
      - db
  scope: Namespaced
  versions:
    - name: v1
      served: true
      storage: true
      schema:
        openAPIV3Schema:
          type: object
          required:
            - spec
          properties:
            spec:
              type: object
              required:
                - engine
                - version
                - storage
              properties:
                engine:
                  type: string
                  enum: [postgres, mysql, mongodb]
                version:
                  type: string
                storage:
                  type: string
                  pattern: '^[0-9]+Gi$'
                replicas:
                  type: integer
                  minimum: 1
                  maximum: 5
                  default: 1
            status:
              type: object
              properties:
                phase:
                  type: string
                  enum:
                    - Pending
                    - Creating
                    - Running
                    - Failed
                    - Terminating
                ready:
                  type: boolean
                message:
                  type: string
                endpoint:
                  type: string
      subresources:
        status: {}
        scale:
          specReplicasPath: .spec.replicas
          statusReplicasPath: .status.replicas
      additionalPrinterColumns:
        - name: Engine
          type: string
          jsonPath: .spec.engine
        - name: Version
          type: string
          jsonPath: .spec.version
        - name: Status
          type: string
          jsonPath: .status.phase
        - name: Age
          type: date
          jsonPath: .metadata.creationTimestamp
```

## Custom Resource Instance

```yaml
apiVersion: mycompany.io/v1
kind: Database
metadata:
  name: orders-db
  namespace: production
spec:
  engine: postgres
  version: "15.4"
  storage: 100Gi
  replicas: 3
```

## Operator SDK Project Structure

```text
my-operator/
├── Dockerfile
├── Makefile
├── PROJECT                        # Kubebuilder project config
├── config/
│   ├── crd/
│   │   └── bases/
│   │       └── mycompany.io_databases.yaml
│   ├── manager/
│   │   └── manager.yaml
│   ├── rbac/
│   │   ├── role.yaml
│   │   ├── role_binding.yaml
│   │   └── service_account.yaml
│   └── samples/
│       └── mycompany_v1_database.yaml
├── api/
│   └── v1/
│       ├── database_types.go      # API type definitions
│       ├── groupversion_info.go
│       └── zz_generated.deepcopy.go
├── controllers/
│   └── database_controller.go     # Reconciliation logic
├── main.go                        # Entry point
└── go.mod
```

## API Type Definition (Go)

```go
// api/v1/database_types.go
package v1

import (
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
)

// DatabaseSpec defines the desired state of Database
type DatabaseSpec struct {
    // +kubebuilder:validation:Enum=postgres;mysql;mongodb
    Engine string `json:"engine"`

    Version string `json:"version"`

    // +kubebuilder:validation:Pattern=`^[0-9]+Gi$`
    Storage string `json:"storage"`

    // +kubebuilder:validation:Minimum=1
    // +kubebuilder:validation:Maximum=5
    // +kubebuilder:default=1
    // +optional
    Replicas int32 `json:"replicas,omitempty"`
}

// DatabaseStatus defines the observed state of Database
type DatabaseStatus struct {
    Phase    string `json:"phase,omitempty"`
    Ready    bool   `json:"ready,omitempty"`
    Message  string `json:"message,omitempty"`
    Endpoint string `json:"endpoint,omitempty"`
    Replicas int32  `json:"replicas,omitempty"`
}

// +kubebuilder:object:root=true
// +kubebuilder:subresource:status
// +kubebuilder:subresource:scale:specpath=.spec.replicas,statuspath=.status.replicas
// +kubebuilder:printcolumn:name="Engine",type=string,JSONPath=`.spec.engine`
// +kubebuilder:printcolumn:name="Version",type=string,JSONPath=`.spec.version`
// +kubebuilder:printcolumn:name="Status",type=string,JSONPath=`.status.phase`
// +kubebuilder:printcolumn:name="Age",type="date",JSONPath=".metadata.creationTimestamp"

// Database is the Schema for the databases API
type Database struct {
    metav1.TypeMeta   `json:",inline"`
    metav1.ObjectMeta `json:"metadata,omitempty"`

    Spec   DatabaseSpec   `json:"spec,omitempty"`
    Status DatabaseStatus `json:"status,omitempty"`
}

// +kubebuilder:object:root=true

// DatabaseList contains a list of Database
type DatabaseList struct {
    metav1.TypeMeta `json:",inline"`
    metav1.ListMeta `json:"metadata,omitempty"`
    Items           []Database `json:"items"`
}

func init() {
    SchemeBuilder.Register(&Database{}, &DatabaseList{})
}
```

## Controller Implementation

```go
// controllers/database_controller.go
package controllers

import (
    "context"
    "fmt"
    "time"

    appsv1 "k8s.io/api/apps/v1"
    corev1 "k8s.io/api/core/v1"
    "k8s.io/apimachinery/pkg/api/errors"
    "k8s.io/apimachinery/pkg/api/resource"
    metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
    "k8s.io/apimachinery/pkg/runtime"
    "k8s.io/apimachinery/pkg/types"
    ctrl "sigs.k8s.io/controller-runtime"
    "sigs.k8s.io/controller-runtime/pkg/client"
    "sigs.k8s.io/controller-runtime/pkg/controller/controllerutil"
    "sigs.k8s.io/controller-runtime/pkg/log"

    mycompanyv1 "github.com/mycompany/database-operator/api/v1"
)

const databaseFinalizer = "databases.mycompany.io/finalizer"

type DatabaseReconciler struct {
    client.Client
    Scheme *runtime.Scheme
}

// +kubebuilder:rbac:groups=mycompany.io,resources=databases,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=mycompany.io,resources=databases/status,verbs=get;update;patch
// +kubebuilder:rbac:groups=mycompany.io,resources=databases/finalizers,verbs=update
// +kubebuilder:rbac:groups=apps,resources=statefulsets,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=services,verbs=get;list;watch;create;update;patch;delete
// +kubebuilder:rbac:groups=core,resources=persistentvolumeclaims,verbs=get;list;watch

func (r *DatabaseReconciler) Reconcile(
    ctx context.Context,
    req ctrl.Request,
) (ctrl.Result, error) {
    logger := log.FromContext(ctx)

    // Fetch the Database instance
    database := &mycompanyv1.Database{}
    if err := r.Get(ctx, req.NamespacedName, database); err != nil {
        if errors.IsNotFound(err) {
            return ctrl.Result{}, nil
        }
        return ctrl.Result{}, err
    }

    // Handle deletion with finalizer
    if !database.DeletionTimestamp.IsZero() {
        if controllerutil.ContainsFinalizer(database, databaseFinalizer) {
            if err := r.cleanupResources(ctx, database); err != nil {
                return ctrl.Result{}, err
            }
            controllerutil.RemoveFinalizer(database, databaseFinalizer)
            if err := r.Update(ctx, database); err != nil {
                return ctrl.Result{}, err
            }
        }
        return ctrl.Result{}, nil
    }

    // Add finalizer if not present
    if !controllerutil.ContainsFinalizer(database, databaseFinalizer) {
        controllerutil.AddFinalizer(database, databaseFinalizer)
        if err := r.Update(ctx, database); err != nil {
            return ctrl.Result{}, err
        }
    }

    // Reconcile StatefulSet
    statefulSet := r.buildStatefulSet(database)
    if err := controllerutil.SetControllerReference(
        database, statefulSet, r.Scheme,
    ); err != nil {
        return ctrl.Result{}, err
    }

    found := &appsv1.StatefulSet{}
    err := r.Get(ctx, types.NamespacedName{
        Name:      statefulSet.Name,
        Namespace: statefulSet.Namespace,
    }, found)
    if err != nil && errors.IsNotFound(err) {
        logger.Info("Creating StatefulSet", "name", statefulSet.Name)
        if err := r.Create(ctx, statefulSet); err != nil {
            return ctrl.Result{}, err
        }
        return r.updateStatus(ctx, database, "Creating", false, "StatefulSet created")
    } else if err != nil {
        return ctrl.Result{}, err
    }

    // Reconcile Service
    service := r.buildService(database)
    if err := controllerutil.SetControllerReference(
        database, service, r.Scheme,
    ); err != nil {
        return ctrl.Result{}, err
    }

    foundSvc := &corev1.Service{}
    err = r.Get(ctx, types.NamespacedName{
        Name:      service.Name,
        Namespace: service.Namespace,
    }, foundSvc)
    if err != nil && errors.IsNotFound(err) {
        if err := r.Create(ctx, service); err != nil {
            return ctrl.Result{}, err
        }
    }

    // Update status based on StatefulSet state
    if found.Status.ReadyReplicas == *found.Spec.Replicas {
        return r.updateStatus(
            ctx, database, "Running", true,
            fmt.Sprintf(
                "%d/%d replicas ready",
                found.Status.ReadyReplicas,
                *found.Spec.Replicas,
            ),
        )
    }

    return ctrl.Result{RequeueAfter: 10 * time.Second}, nil
}

func (r *DatabaseReconciler) buildStatefulSet(
    db *mycompanyv1.Database,
) *appsv1.StatefulSet {
    replicas := db.Spec.Replicas
    labels := map[string]string{
        "app":        db.Name,
        "controller": db.Name,
    }

    return &appsv1.StatefulSet{
        ObjectMeta: metav1.ObjectMeta{
            Name:      db.Name,
            Namespace: db.Namespace,
        },
        Spec: appsv1.StatefulSetSpec{
            Replicas: &replicas,
            Selector: &metav1.LabelSelector{
                MatchLabels: labels,
            },
            ServiceName: db.Name,
            Template: corev1.PodTemplateSpec{
                ObjectMeta: metav1.ObjectMeta{Labels: labels},
                Spec: corev1.PodSpec{
                    Containers: []corev1.Container{{
                        Name:  "database",
                        Image: fmt.Sprintf("%s:%s", db.Spec.Engine, db.Spec.Version),
                        Ports: []corev1.ContainerPort{{
                            ContainerPort: 5432,
                            Name:          "db",
                        }},
                    }},
                },
            },
            VolumeClaimTemplates: []corev1.PersistentVolumeClaim{{
                ObjectMeta: metav1.ObjectMeta{Name: "data"},
                Spec: corev1.PersistentVolumeClaimSpec{
                    AccessModes: []corev1.PersistentVolumeAccessMode{
                        corev1.ReadWriteOnce,
                    },
                    Resources: corev1.VolumeResourceRequirements{
                        Requests: corev1.ResourceList{
                            corev1.ResourceStorage: resource.MustParse(
                                db.Spec.Storage,
                            ),
                        },
                    },
                },
            }},
        },
    }
}

func (r *DatabaseReconciler) buildService(
    db *mycompanyv1.Database,
) *corev1.Service {
    return &corev1.Service{
        ObjectMeta: metav1.ObjectMeta{
            Name:      db.Name,
            Namespace: db.Namespace,
        },
        Spec: corev1.ServiceSpec{
            Selector: map[string]string{"app": db.Name},
            Ports: []corev1.ServicePort{{
                Port: 5432,
                Name: "db",
            }},
            ClusterIP: "None",
        },
    }
}

func (r *DatabaseReconciler) updateStatus(
    ctx context.Context,
    db *mycompanyv1.Database,
    phase string,
    ready bool,
    message string,
) (ctrl.Result, error) {
    db.Status.Phase = phase
    db.Status.Ready = ready
    db.Status.Message = message
    db.Status.Endpoint = fmt.Sprintf(
        "%s.%s.svc.cluster.local:5432", db.Name, db.Namespace,
    )
    return ctrl.Result{}, r.Status().Update(ctx, db)
}

func (r *DatabaseReconciler) cleanupResources(
    ctx context.Context,
    db *mycompanyv1.Database,
) error {
    // Custom cleanup logic (backup before deletion, etc.)
    return nil
}

func (r *DatabaseReconciler) SetupWithManager(
    mgr ctrl.Manager,
) error {
    return ctrl.NewControllerManagedBy(mgr).
        For(&mycompanyv1.Database{}).
        Owns(&appsv1.StatefulSet{}).
        Owns(&corev1.Service{}).
        Complete(r)
}
```

## Operator RBAC

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: database-operator
  namespace: operators
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRole
metadata:
  name: database-operator-role
rules:
  - apiGroups: ["mycompany.io"]
    resources: ["databases"]
    verbs:
      - get
      - list
      - watch
      - create
      - update
      - patch
      - delete
  - apiGroups: ["mycompany.io"]
    resources: ["databases/status"]
    verbs: ["get", "update", "patch"]
  - apiGroups: ["mycompany.io"]
    resources: ["databases/finalizers"]
    verbs: ["update"]
  - apiGroups: ["apps"]
    resources: ["statefulsets"]
    verbs:
      - get
      - list
      - watch
      - create
      - update
      - patch
      - delete
  - apiGroups: [""]
    resources: ["services", "configmaps", "secrets"]
    verbs:
      - get
      - list
      - watch
      - create
      - update
      - patch
      - delete
  - apiGroups: [""]
    resources: ["persistentvolumeclaims"]
    verbs: ["get", "list", "watch"]
  - apiGroups: [""]
    resources: ["events"]
    verbs: ["create", "patch"]
---
apiVersion: rbac.authorization.k8s.io/v1
kind: ClusterRoleBinding
metadata:
  name: database-operator-rolebinding
roleRef:
  apiGroup: rbac.authorization.k8s.io
  kind: ClusterRole
  name: database-operator-role
subjects:
  - kind: ServiceAccount
    name: database-operator
    namespace: operators
```

## Operator Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: database-operator
  namespace: operators
  labels:
    app: database-operator
spec:
  replicas: 1
  selector:
    matchLabels:
      app: database-operator
  template:
    metadata:
      labels:
        app: database-operator
    spec:
      serviceAccountName: database-operator
      securityContext:
        runAsNonRoot: true
        seccompProfile:
          type: RuntimeDefault
      containers:
        - name: manager
          image: myregistry.io/database-operator:v1.0.0
          args:
            - --leader-elect
            - --health-probe-bind-address=:8081
          securityContext:
            allowPrivilegeEscalation: false
            capabilities:
              drop: ["ALL"]
            readOnlyRootFilesystem: true
          ports:
            - containerPort: 8080
              name: metrics
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8081
            initialDelaySeconds: 15
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8081
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            limits:
              cpu: 500m
              memory: 128Mi
            requests:
              cpu: 10m
              memory: 64Mi
```

## Operator SDK Commands

```bash
# Initialize new operator project
operator-sdk init \
  --domain mycompany.io \
  --repo github.com/mycompany/database-operator

# Create new API (CRD + controller)
operator-sdk create api \
  --group mycompany --version v1 --kind Database \
  --resource --controller

# Generate manifests (CRD, RBAC)
make manifests

# Generate deep copy methods
make generate

# Build and push operator image
make docker-build docker-push \
  IMG=myregistry.io/database-operator:v1.0.0

# Deploy to cluster
make deploy IMG=myregistry.io/database-operator:v1.0.0

# Undeploy
make undeploy
```

## Best Practices

1. **Finalizers** — clean up external resources before CR deletion
2. **Owner references** — owned resources garbage-collected with the CR
3. **Idempotent reconciliation** — same input always produces same output
4. **Status subresource** — separate desired state (spec) from observed (status)
5. **Validation** — openAPIV3Schema in the CRD plus admission webhooks
6. **Events** — emit for significant state changes
7. **Leader election** — `--leader-elect` for HA operator deployments
8. **Resource limits** — set on the operator Deployment itself
9. **Least privilege** — RBAC only for resources the operator manages
10. **envtest** — unit-test controllers with the controller-runtime envtest package
