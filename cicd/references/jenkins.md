# Jenkins Pipelines

## Declarative Pipeline

Standard Jenkinsfile with build, test, security, and deploy stages.

```groovy
pipeline {
    agent any

    environment {
        DOCKER_REGISTRY = 'registry.example.com'
        IMAGE_NAME = "${DOCKER_REGISTRY}/app"
        IMAGE_TAG = "${env.BUILD_NUMBER}-${env.GIT_COMMIT?.take(7)}"
    }

    options {
        timeout(time: 60, unit: 'MINUTES')
        retry(1)
        disableConcurrentBuilds()
        buildDiscarder(logRotator(numToKeepStr: '20'))
    }

    stages {
        stage('Checkout') {
            steps {
                checkout scm
            }
        }

        stage('Lint') {
            steps {
                sh 'npm ci'
                sh 'npm run lint'
            }
        }

        stage('Test') {
            parallel {
                stage('Unit Tests') {
                    steps {
                        sh 'npm test -- --coverage'
                    }
                    post {
                        always {
                            junit 'test-results/**/*.xml'
                            publishHTML([
                                reportName: 'Coverage',
                                reportDir: 'coverage/lcov-report',
                                reportFiles: 'index.html'
                            ])
                        }
                    }
                }
                stage('Integration Tests') {
                    steps {
                        sh 'npm run test:integration'
                    }
                }
            }
        }

        stage('Security Scan') {
            steps {
                sh 'trivy fs --exit-code 1 --severity HIGH,CRITICAL .'
            }
        }

        stage('Build Docker') {
            steps {
                script {
                    docker.withRegistry("https://${DOCKER_REGISTRY}", 'docker-creds') {
                        def image = docker.build("${IMAGE_NAME}:${IMAGE_TAG}")
                        image.push()
                        image.push('latest')
                    }
                }
            }
        }

        stage('Deploy Staging') {
            when {
                branch 'develop'
            }
            steps {
                sh """
                    kubectl set image deployment/app \
                        app=${IMAGE_NAME}:${IMAGE_TAG} \
                        --namespace=staging
                    kubectl rollout status deployment/app \
                        --namespace=staging --timeout=5m
                """
            }
        }

        stage('Deploy Production') {
            when {
                branch 'main'
            }
            input {
                message 'Deploy to production?'
                ok 'Deploy'
            }
            steps {
                sh """
                    kubectl set image deployment/app \
                        app=${IMAGE_NAME}:${IMAGE_TAG} \
                        --namespace=production
                    kubectl rollout status deployment/app \
                        --namespace=production --timeout=5m
                """
            }
        }
    }

    post {
        always {
            cleanWs()
        }
        failure {
            slackSend(
                color: 'danger',
                message: "Build FAILED: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
            )
        }
        success {
            slackSend(
                color: 'good',
                message: "Build PASSED: ${env.JOB_NAME} #${env.BUILD_NUMBER}"
            )
        }
    }
}
```

## Scripted Pipeline with Shared Library

Use shared libraries for reusable pipeline logic across projects.

### Shared library structure

```text
jenkins-shared-lib/
├── vars/
│   ├── buildAndTest.groovy
│   └── deployService.groovy
└── src/org/example/
    └── PipelineUtils.groovy
```

### vars/buildAndTest.groovy

```groovy
def call(Map config = [:]) {
    def nodeVersion = config.nodeVersion ?: '20'
    def runE2e = config.runE2e ?: false

    pipeline {
        agent { docker { image "node:${nodeVersion}" } }

        stages {
            stage('Install') {
                steps {
                    sh 'npm ci'
                }
            }
            stage('Lint') {
                steps {
                    sh 'npm run lint'
                }
            }
            stage('Unit Test') {
                steps {
                    sh 'npm test'
                }
            }
            stage('E2E Test') {
                when { expression { runE2e } }
                steps {
                    sh 'npm run test:e2e'
                }
            }
            stage('Build') {
                steps {
                    sh 'npm run build'
                }
            }
        }
    }
}
```

### vars/deployService.groovy

```groovy
def call(Map config) {
    def env = config.environment
    def image = config.image
    def namespace = config.namespace ?: env

    sh """
        kubectl set image deployment/${config.service} \
            ${config.service}=${image} \
            --namespace=${namespace}
        kubectl rollout status deployment/${config.service} \
            --namespace=${namespace} --timeout=5m
    """
}
```

### Caller Jenkinsfile

```groovy
@Library('jenkins-shared-lib') _

buildAndTest(nodeVersion: '20', runE2e: true)
```

## Parallel Stage Execution

```groovy
stage('Quality Gates') {
    parallel {
        stage('Lint') {
            steps {
                sh 'npm run lint'
            }
        }
        stage('SAST') {
            steps {
                sh 'semgrep scan --config auto .'
            }
        }
        stage('Unit Tests') {
            steps {
                sh 'npm test'
            }
        }
    }
}
```

## Docker Agent

Run stages inside specific Docker containers.

```groovy
pipeline {
    agent none

    stages {
        stage('Test') {
            agent {
                docker {
                    image 'node:20'
                    args '-v $HOME/.npm:/root/.npm'
                }
            }
            steps {
                sh 'npm ci && npm test'
            }
        }

        stage('Build Image') {
            agent {
                docker {
                    image 'docker:24'
                    args '-v /var/run/docker.sock:/var/run/docker.sock'
                }
            }
            steps {
                sh 'docker build -t app:latest .'
            }
        }
    }
}
```

## Credentials Management

```groovy
stage('Deploy') {
    steps {
        withCredentials([
            usernamePassword(
                credentialsId: 'docker-registry',
                usernameVariable: 'DOCKER_USER',
                passwordVariable: 'DOCKER_PASS'
            ),
            string(
                credentialsId: 'kube-token',
                variable: 'KUBE_TOKEN'
            )
        ]) {
            sh 'docker login -u $DOCKER_USER -p $DOCKER_PASS registry.example.com'
            sh 'kubectl --token=$KUBE_TOKEN apply -f k8s/'
        }
    }
}
```

## Pipeline Parameters

```groovy
pipeline {
    parameters {
        choice(
            name: 'ENVIRONMENT',
            choices: ['staging', 'production'],
            description: 'Target deployment environment'
        )
        string(
            name: 'VERSION',
            defaultValue: '',
            description: 'Version tag to deploy'
        )
        booleanParam(
            name: 'SKIP_TESTS',
            defaultValue: false,
            description: 'Skip test stages'
        )
    }

    stages {
        stage('Test') {
            when { expression { !params.SKIP_TESTS } }
            steps {
                sh 'npm test'
            }
        }
        stage('Deploy') {
            steps {
                echo "Deploying ${params.VERSION} to ${params.ENVIRONMENT}"
            }
        }
    }
}
```

## Blue Ocean Multibranch

Configure multibranch pipelines for automatic branch discovery.

```groovy
// Jenkinsfile (in each branch)
pipeline {
    agent any

    stages {
        stage('Build') {
            steps {
                sh 'npm ci && npm run build'
            }
        }
        stage('Deploy') {
            when {
                anyOf {
                    branch 'main'
                    branch 'develop'
                }
            }
            steps {
                script {
                    def targetEnv = env.BRANCH_NAME == 'main' ? 'production' : 'staging'
                    sh "kubectl apply -f k8s/overlays/${targetEnv}"
                }
            }
        }
    }
}
```
