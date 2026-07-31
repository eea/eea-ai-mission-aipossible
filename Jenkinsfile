pipeline {
  agent {
    node { label 'docker-host' }
  }

  options {
    timestamps()
    disableConcurrentBuilds()
  }

  environment {
    IMAGE_BASENAME_TEST = 'mission-aipossible-test'
    IMAGE_BASENAME_RELEASE = 'mission-aipossible-release'
    DOCKERHUB_REPOSITORY = 'eeacms/eea-ai-mission-aipossible'
    DOCKERHUB_CREDENTIALS_ID = 'dockerhub'
    SONARQUBE_SERVER = 'Sonarqube'
    SONAR_SCANNER_TOOL = 'SonarQubeScanner'
    TRIVY_IMAGE = 'aquasec/trivy:0.57.1'
    REPORTS_DIR = 'xunit-reports-current'
    INTEGRATION_REPORTS_DIR = 'integration-reports-current'
    APP_PORT = '18000'
  }

  stages {
    stage('Versioning') {
      steps {
        script {
          env.BASE_VERSION = sh(returnStdout: true, script: "jq -r '.version' ui/package.json").trim()
          env.GIT_SHA_SHORT = sh(returnStdout: true, script: 'git rev-parse --short=8 HEAD').trim()
          env.SANITIZED_BRANCH = (env.BRANCH_NAME ?: 'detached').replaceAll(/[^A-Za-z0-9_.-]+/, '-')
          env.VERSION = (env.BRANCH_NAME == 'main' || env.TAG_NAME) ? env.BASE_VERSION : "${env.BASE_VERSION}-${env.SANITIZED_BRANCH}-${env.BUILD_NUMBER}-${env.GIT_SHA_SHORT}"
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
          mkdir -p xunit-reports-current/coverage integration-reports-current/coverage .jenkins-fixtures
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
              docker run --rm "$TEST_IMAGE" bash -lc '
                ruff check analysis api pre_analysis exporters scripts adaptation_stories tests main.py env_settings.py --select E,F,W,I,B,C,N,Q,RUF --ignore D &&
                black --check analysis api pre_analysis exporters scripts adaptation_stories tests main.py env_settings.py &&
                mypy analysis api pre_analysis exporters scripts adaptation_stories
              '
            '''
          }
        }
        stage('UI production build') {
          steps {
            sh '''
              docker run --rm "$TEST_IMAGE" bash -lc 'cd /app/ui && npm run build'
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
              docker run --name "$UNIT_CONTAINER" "$TEST_IMAGE" bash -lc '
                mkdir -p /app/reports/coverage &&
                pytest tests \
                  --ignore=tests/test_analysis_api.py \
                  --ignore=tests/test_run_analysis_api_script.py \
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
                -p 127.0.0.1:${APP_PORT}:8000 \
                -e OUTPUT_DIR=/app/data/analysis \
                -e EXPORT_DIR=/app/data/exports \
                -e PROVIDER=mock \
                -e API_USE_CASES_CONFIG=/tmp/analysis_use_cases.json \
                "$RELEASE_IMAGE"
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
              docker run --name "$IT_CONTAINER" "$TEST_IMAGE" bash -lc '
                mkdir -p /app/reports/coverage &&
                pytest tests/test_analysis_api.py tests/test_run_analysis_api_script.py \
                  --junitxml=/app/reports/junit.xml \
                  --cov=. \
                  --cov-report=term-missing \
                  --cov-report=lcov:/app/reports/coverage/lcov.info \
                  --cov-report=xml:/app/reports/coverage/coverage.xml \
                  --cov-report=html:/app/reports/coverage/lcov-report
              '
            ''')
            def itJunitCp = sh(script: 'docker cp "$IT_CONTAINER":/app/reports/junit.xml integration-reports-current/junit.xml', returnStatus: true)
            if (itJunitCp != 0) {
              echo "WARNING: docker cp of integration junit.xml failed (exit ${itJunitCp}) — Sonarqube will see no integration test results"
            }
            def itCovCp = sh(script: 'docker cp "$IT_CONTAINER":/app/reports/coverage/. integration-reports-current/coverage', returnStatus: true)
            if (itCovCp != 0) {
              echo "WARNING: docker cp of integration coverage failed (exit ${itCovCp}) — Sonarqube will see 0% integration coverage"
            }
          } finally {
            catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
              junit testResults: 'integration-reports-current/junit.xml', allowEmptyResults: true
            }
            catchError(buildResult: 'SUCCESS', stageResult: 'SUCCESS') {
              publishHTML(target: [
                allowMissing: true,
                alwaysLinkToLastBuild: true,
                keepAll: true,
                reportDir: 'integration-reports-current/coverage/lcov-report',
                reportFiles: 'index.html',
                reportName: 'ITCoverage',
                reportTitles: 'Integration Tests Code Coverage'
              ])
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
          // Confirm what's actually on disk before scanning — if a report is
          // missing, this makes it obvious in the log instead of only
          // showing up as a cryptic "no report found" warning from Sonar.
          sh '''
            echo "--- report files feeding Sonarqube ---"
            ls -la xunit-reports-current integration-reports-current \
              xunit-reports-current/coverage integration-reports-current/coverage 2>&1 || true
          '''
          withSonarQubeEnv(env.SONARQUBE_SERVER) {
            sh """
              export PATH=${scannerHome}/bin:$PATH
              sonar-scanner \
                -Dsonar.projectKey=eea-ai-mission-aipossible \
                -Dsonar.projectName=eea-ai-mission-aipossible \
                -Dsonar.projectVersion=${env.VERSION} \
                -Dsonar.sources=./adaptation_stories,./analysis,./api,./exporters,./pre_analysis,./scripts,./ui/src \
                -Dsonar.tests=./tests \
                -Dsonar.junit.reportPaths=./xunit-reports-current/junit.xml,./integration-reports-current/junit.xml \
                -Dsonar.python.xunit.reportPath=./*-reports-current/junit.xml \
                -Dsonar.python.coverage.reportPaths=./xunit-reports-current/coverage/coverage.xml,./integration-reports-current/coverage/coverage.xml \
                -Dsonar.coverage.exclusions=ui/src/**,adaptation_stories/settings.py,adaptation_stories/middlewares.py,adaptation_stories/pipelines.py,main.py,scripts/run_analysis_api.py,scripts/run_pre_analysis.py \
                ${env.sonarParams}
            """
          }
        }
      }
    }

    stage('Trivy test') {
      steps {
        // .trivyignore lives in the checked-out workspace, but the trivy
        // container can't see it via a bind mount (see the EEA
        // Docker-outside-of-Docker constraint) — create the container,
        // docker cp the ignore file in, then start it.
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

        // Only CRITICAL findings fail the build; HIGH findings are visible
        // in the archived report above but don't block the pipeline.
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
          branch 'main'
          buildingTag()
        }
      }
      steps {
        withCredentials([usernamePassword(credentialsId: env.DOCKERHUB_CREDENTIALS_ID, usernameVariable: 'DOCKERHUB_USERNAME', passwordVariable: 'DOCKERHUB_PASSWORD')]) {
          sh '''
            set -euo pipefail
            echo "$DOCKERHUB_PASSWORD" | docker login -u "$DOCKERHUB_USERNAME" --password-stdin
            docker tag "$RELEASE_IMAGE" "$DOCKERHUB_VERSION_TAG"
            docker push "$DOCKERHUB_VERSION_TAG"
            if [ "$BRANCH_NAME" = "main" ]; then
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
