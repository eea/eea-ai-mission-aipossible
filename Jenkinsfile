pipeline {
  agent {
    node { label 'docker-host' }
  }

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  environment {
    // Checked via the GitHub API (repos/eea/eea-ai-mission-aipossible ->
    // default_branch), not assumed — EEA repos aren't all on 'main'.
    DEFAULT_BRANCH = 'main'
    IMAGE_BASENAME_TEST = 'mission-aipossible-test'
    IMAGE_BASENAME_RELEASE = 'mission-aipossible-release'
    DOCKERHUB_REPOSITORY = 'eeacms/eea-ai-mission-aipossible'
    DOCKERHUB_CREDENTIALS_ID = 'jekinsdockerhub'
    SONARQUBE_SERVER = 'Sonarqube'
    SONAR_SCANNER_TOOL = 'SonarQubeScanner'
    TRIVY_IMAGE = 'aquasec/trivy:0.57.1'
    REPORTS_DIR = 'xunit-reports-current'
    INTEGRATION_REPORTS_DIR = 'integration-reports-current'
    APP_PORT = '18000'
  }

  stages {
    stage('Checkout') {
      steps {
        checkout scm
      }
    }

    stage('Versioning') {
      steps {
        script {
          env.BASE_VERSION = sh(
            returnStdout: true,
            script: "grep -m1 '^version' pyproject.toml | sed -E 's/version = \"(.*)\"/\\1/'"
          ).trim()
          env.GIT_SHA_SHORT = sh(returnStdout: true, script: 'git rev-parse --short=8 HEAD').trim()
          env.SANITIZED_BRANCH = (env.BRANCH_NAME ?: 'detached').replaceAll(/[^A-Za-z0-9_.-]+/, '-')
          if (env.TAG_NAME) {
            // The Docker image tag is always the git tag itself,
            // unconditionally — never gated on matching pyproject.toml. A
            // mismatch is only a warning: alpha/beta/rc pre-releases, a
            // v-prefixed tag convention, or a pyproject.toml that's
            // deliberately not bumped until later are all legitimate, and
            // hard-failing would block a release the developer explicitly
            // asked for by pushing the tag.
            env.VERSION = env.TAG_NAME
            def normalizedTag = env.TAG_NAME.replaceFirst(/^v/, '')
            if (env.BASE_VERSION != env.TAG_NAME && env.BASE_VERSION != normalizedTag) {
              echo "WARNING: git tag (${env.TAG_NAME}) does not match pyproject.toml version (${env.BASE_VERSION}) — pushing ${env.VERSION} anyway. Bump pyproject.toml to match if this wasn't intentional."
              currentBuild.result = 'UNSTABLE'
            }
          } else if (env.BRANCH_NAME == env.DEFAULT_BRANCH) {
            env.VERSION = env.BASE_VERSION
          } else {
            env.VERSION = "${env.BASE_VERSION}-${env.SANITIZED_BRANCH}-${env.BUILD_NUMBER}-${env.GIT_SHA_SHORT}"
          }
          env.TEST_IMAGE = "${env.IMAGE_BASENAME_TEST}:${env.BUILD_NUMBER}"
          env.RELEASE_IMAGE = "${env.IMAGE_BASENAME_RELEASE}:${env.BUILD_NUMBER}"
          env.DOCKERHUB_VERSION_TAG = "${env.DOCKERHUB_REPOSITORY}:${env.VERSION}"
          env.DOCKERHUB_LATEST_TAG = "${env.DOCKERHUB_REPOSITORY}:latest"
          env.APP_CONTAINER = "mission-aipossible-api-${env.BUILD_TAG}".replaceAll(/[^A-Za-z0-9_.-]+/, '-')
          env.UNIT_CONTAINER = "mission-aipossible-unit-${env.BUILD_TAG}".replaceAll(/[^A-Za-z0-9_.-]+/, '-')
          env.IT_CONTAINER = "mission-aipossible-it-${env.BUILD_TAG}".replaceAll(/[^A-Za-z0-9_.-]+/, '-')
          env.TRIVY_CONTAINER = "mission-aipossible-trivy-${env.BUILD_TAG}".replaceAll(/[^A-Za-z0-9_.-]+/, '-')
          env.TRIVY_GATE_CONTAINER = "mission-aipossible-trivy-gate-${env.BUILD_TAG}".replaceAll(/[^A-Za-z0-9_.-]+/, '-')
        }
        sh '''
          rm -rf xunit-reports-current integration-reports-current .jenkins-fixtures
          mkdir -p xunit-reports-current/coverage integration-reports-current .jenkins-fixtures
        '''
      }
    }

    stage('Build test image') {
      steps {
        sh 'docker build -f Dockerfile.test -t "$TEST_IMAGE" .'
      }
    }

    stage('Code linting') {
      parallel {
        stage('Python quality checks') {
          steps {
            sh '''
              docker run --rm "$TEST_IMAGE" bash -c '
                ruff check analysis api pre_analysis exporters scripts adaptation_stories tests tests_integration main.py env_settings.py --ignore D &&
                black --check analysis api pre_analysis exporters scripts adaptation_stories tests tests_integration main.py env_settings.py &&
                mypy analysis api pre_analysis exporters scripts adaptation_stories
              '
            '''
          }
        }
        stage('UI production build') {
          steps {
            sh '''
              docker run --rm "$TEST_IMAGE" bash -c 'cd /app/ui && npm run build'
            '''
          }
        }
      }
    }

    stage('Unit test') {
      steps {
        script {
          def unitStatus = 0
          try {
            unitStatus = sh(returnStatus: true, script: '''
              docker run --name "$UNIT_CONTAINER" "$TEST_IMAGE" bash -c '
                mkdir -p /app/reports/coverage &&
                pytest tests \
                  --junitxml=/app/reports/junit.xml \
                  --cov=. \
                  --cov-report=term-missing \
                  --cov-report=lcov:/app/reports/coverage/lcov.info \
                  --cov-report=xml:/app/reports/coverage/coverage.xml \
                  --cov-report=html:/app/reports/coverage/lcov-report
              '
            ''')
            def unitJunitCp = sh(script: 'docker cp "$UNIT_CONTAINER":/app/reports/junit.xml xunit-reports-current/junit.xml', returnStatus: true)
            if (unitJunitCp != 0) {
              echo "WARNING: docker cp of unit junit.xml failed (exit ${unitJunitCp}) — Sonarqube will see no unit test results"
            }
            def unitCovCp = sh(script: 'docker cp "$UNIT_CONTAINER":/app/reports/coverage/. xunit-reports-current/coverage', returnStatus: true)
            if (unitCovCp != 0) {
              echo "WARNING: docker cp of unit coverage failed (exit ${unitCovCp}) — Sonarqube will see 0% unit coverage"
            }
          } finally {
            catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
              junit testResults: 'xunit-reports-current/junit.xml', allowEmptyResults: true
            }
            catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
              publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'xunit-reports-current/coverage/lcov-report',
                reportFiles: 'index.html',
                reportName: 'UTCoverage',
                reportTitles: 'Unit Tests Code Coverage'
              ])
            }
            sh script: 'docker rm -v "$UNIT_CONTAINER"', returnStatus: true
          }
          if (unitStatus != 0) {
            error('Unit tests failed')
          }
        }
      }
    }

    stage('Build release image') {
      steps {
        sh 'docker build -t "$RELEASE_IMAGE" .'
      }
    }

    stage('Integration test') {
      steps {
        script {
          def integrationStatus = 0
          try {
            sh '''
              set -euo pipefail
              printf '{"smoke_use_case": {}}' > .jenkins-fixtures/analysis_use_cases.json

              docker create \
                --name "$APP_CONTAINER" \
                --network host \
                -e OUTPUT_DIR=/app/data/analysis \
                -e EXPORT_DIR=/app/data/exports \
                -e PROVIDER=mock \
                -e API_USE_CASES_CONFIG=/tmp/analysis_use_cases.json \
                "$RELEASE_IMAGE" \
                uvicorn api.app:app --host 0.0.0.0 --port "$APP_PORT"
              docker cp .jenkins-fixtures/analysis_use_cases.json "$APP_CONTAINER":/tmp/analysis_use_cases.json
              docker start "$APP_CONTAINER"

              for _ in $(seq 1 30); do
                curl -fsS "http://127.0.0.1:${APP_PORT}/health" >/dev/null && break
                sleep 2
              done

              curl -fsS "http://127.0.0.1:${APP_PORT}/health" >/dev/null
              curl -fsS "http://127.0.0.1:${APP_PORT}/v1/analysis/use-cases" >/dev/null
            '''

            integrationStatus = sh(returnStatus: true, script: '''
              docker run --name "$IT_CONTAINER" --network host -e API_BASE_URL="http://127.0.0.1:${APP_PORT}" "$TEST_IMAGE" bash -c '
                mkdir -p /app/reports &&
                pytest tests_integration --junitxml=/app/reports/junit.xml
              '
            ''')
            def itJunitCp = sh(script: 'docker cp "$IT_CONTAINER":/app/reports/junit.xml integration-reports-current/junit.xml', returnStatus: true)
            if (itJunitCp != 0) {
              echo "WARNING: docker cp of integration junit.xml failed (exit ${itJunitCp}) — Sonarqube will see no integration test results"
            }
          } finally {
            catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
              junit testResults: 'integration-reports-current/junit.xml', allowEmptyResults: true
            }
            sh script: 'docker rm -fv "$APP_CONTAINER"', returnStatus: true
            sh script: 'docker rm -v "$IT_CONTAINER"', returnStatus: true
          }
          if (integrationStatus != 0) {
            error('Integration tests failed')
          }
        }
      }
    }

    stage('Sonarqube test') {
      steps {
        script {
          def scannerHome = tool env.SONAR_SCANNER_TOOL
          if (env.CHANGE_ID) {
            env.sonarParams = " -Dsonar.pullrequest.base=${env.CHANGE_TARGET} -Dsonar.pullrequest.branch=${env.CHANGE_BRANCH} -Dsonar.pullrequest.key=${env.CHANGE_ID} "
          } else {
            env.sonarParams = " -Dsonar.branch.name=${env.BRANCH_NAME} "
          }
          sh '''
            echo "--- report files feeding Sonarqube ---"
            ls -la xunit-reports-current integration-reports-current xunit-reports-current/coverage 2>&1 || true
          '''
          withSonarQubeEnv(env.SONARQUBE_SERVER) {
            sh """
              export PATH=${scannerHome}/bin:\$PATH
              sonar-scanner \
                -Dsonar.projectKey=eea-ai-mission-aipossible \
                -Dsonar.projectName=eea-ai-mission-aipossible \
                -Dsonar.projectVersion=${env.VERSION} \
                -Dsonar.sources=./adaptation_stories,./analysis,./api,./exporters,./pre_analysis,./scripts,./ui/src \
                -Dsonar.tests=./tests,./tests_integration \
                -Dsonar.python.coverage.reportPaths=./xunit-reports-current/coverage/coverage.xml \
                -Dsonar.coverage.exclusions=ui/src/**,adaptation_stories/settings.py,adaptation_stories/middlewares.py,adaptation_stories/pipelines.py,main.py \
                ${env.sonarParams}
            """
            sh '''
              curl -s -XPOST -u "${SONAR_AUTH_TOKEN}:" "${SONAR_HOST_URL}api/alm_settings/set_github_binding" \
                -d "almSetting=GitHubEEA" \
                -d "project=eea-ai-mission-aipossible" \
                -d "repository=eea/eea-ai-mission-aipossible" \
                -d "summaryCommentEnabled=true"
            '''
          }
        }
      }
    }

    stage('Trivy test') {
      steps {
        sh '''
          mkdir -p trivy-reports

          docker create --name "$TRIVY_CONTAINER" \
            -v /var/run/docker.sock:/var/run/docker.sock \
            "$TRIVY_IMAGE" image --no-progress --format table --severity HIGH,CRITICAL \
            --ignorefile /tmp/.trivyignore --output /tmp/trivy-image.txt "$RELEASE_IMAGE"
          docker cp .trivyignore "$TRIVY_CONTAINER":/tmp/.trivyignore
          docker start -a "$TRIVY_CONTAINER" || true
          docker cp "$TRIVY_CONTAINER":/tmp/trivy-image.txt trivy-reports/trivy-image.txt
          docker rm -v "$TRIVY_CONTAINER"
        '''
        archiveArtifacts artifacts: 'trivy-reports/*.txt', fingerprint: true, allowEmptyArchive: false

        sh '''
          docker create --name "$TRIVY_GATE_CONTAINER" \
            -v /var/run/docker.sock:/var/run/docker.sock \
            "$TRIVY_IMAGE" image --no-progress --severity CRITICAL --exit-code 1 \
            --ignorefile /tmp/.trivyignore "$RELEASE_IMAGE"
          docker cp .trivyignore "$TRIVY_GATE_CONTAINER":/tmp/.trivyignore
          docker start -a "$TRIVY_GATE_CONTAINER"
          status=$?
          docker rm -v "$TRIVY_GATE_CONTAINER"
          exit $status
        '''
      }
    }

    stage('Release on Docker Hub') {
      when {
        anyOf {
          expression { env.BRANCH_NAME == env.DEFAULT_BRANCH }
          buildingTag()
        }
      }
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDENTIALS_ID, usernameVariable: 'DOCKERHUB_USERNAME', passwordVariable: 'DOCKERHUB_PASSWORD')]) {
          sh '''
            set -euo pipefail
            echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
            # A version-numbered tag must correspond to an actual git tag
            # (release) — a plain main-branch merge only updates :latest,
            # otherwise every merge would push a "0.1.0" image before
            # 0.1.0 has actually been released.
            if [ -n "${TAG_NAME:-}" ]; then
              docker tag "$RELEASE_IMAGE" "$DOCKERHUB_VERSION_TAG"
              docker push "$DOCKERHUB_VERSION_TAG"
            fi
            if [ "$BRANCH_NAME" = "$DEFAULT_BRANCH" ]; then
              docker tag "$RELEASE_IMAGE" "$DOCKERHUB_LATEST_TAG"
              docker push "$DOCKERHUB_LATEST_TAG"
            fi
            docker logout
          '''
        }
      }
    }
  }
  post {
    always {
      sh '''
        docker rm -fv "$APP_CONTAINER" >/dev/null 2>&1 || true
        docker rm -fv "$UNIT_CONTAINER" >/dev/null 2>&1 || true
        docker rm -fv "$IT_CONTAINER" >/dev/null 2>&1 || true
        docker rm -fv "$TRIVY_CONTAINER" >/dev/null 2>&1 || true
        docker rm -fv "$TRIVY_GATE_CONTAINER" >/dev/null 2>&1 || true
      '''
      cleanWs(cleanWhenAborted: true, cleanWhenFailure: true, cleanWhenNotBuilt: true, cleanWhenSuccess: true, cleanWhenUnstable: true, deleteDirs: true)
    }
    changed {
      script {
        def details = """<h1>${env.JOB_NAME} - Build #${env.BUILD_NUMBER} - ${currentBuild.currentResult}</h1>
                         <p>Check console output at <a href="${env.BUILD_URL}/display/redirect">${env.JOB_BASE_NAME} - #${env.BUILD_NUMBER}</a></p>
                      """
        emailext(
        subject: '$DEFAULT_SUBJECT',
        body: details,
        attachLog: true,
        compressLog: true,
        recipientProviders: [[$class: 'DevelopersRecipientProvider'], [$class: 'CulpritsRecipientProvider']]
        )
      }
    }
  }
}
