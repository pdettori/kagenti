// Copyright 2025 IBM Corp.
// Licensed under the Apache License, Version 2.0

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  PageSection,
  Title,
  Text,
  TextContent,
  Card,
  CardTitle,
  CardBody,
  Form,
  FormGroup,
  TextInput,
  FormSelect,
  FormSelectOption,
  Button,
  Alert,
  Split,
  SplitItem,
  ExpandableSection,
  ActionGroup,
  FormHelperText,
  HelperText,
  HelperTextItem,
  Divider,
  Radio,
  NumberInput,
  Grid,
  GridItem,
} from '@patternfly/react-core';
import { TrashIcon, PlusCircleIcon } from '@patternfly/react-icons';
import { useMutation } from '@tanstack/react-query';

import { agentService } from '@/services/api';
import { NamespaceSelector } from '@/components/NamespaceSelector';

// Example agent subfolders from the original UI
const AGENT_EXAMPLES = [
  { value: '', label: 'Select an example...' },
  { value: 'a2a/a2a_contact_extractor', label: 'Contact Extractor Agent' },
  { value: 'a2a/a2a_currency_converter', label: 'Currency Converter Agent' },
  { value: 'a2a/generic_agent', label: 'Generic Agent' },
  { value: 'a2a/git_issue_agent', label: 'Git Issue Agent' },
  { value: 'a2a/file_organizer', label: 'File Organizer Agent' },
  { value: 'a2a/slack_researcher', label: 'Slack Researcher Agent' },
  { value: 'a2a/weather_service', label: 'Weather Service Agent' },
];

const FRAMEWORKS = [
  { value: 'LangGraph', label: 'LangGraph' },
  { value: 'CrewAI', label: 'CrewAI' },
  { value: 'AG2', label: 'AG2' },
  { value: 'Python', label: 'Python (Custom)' },
];

const REGISTRY_OPTIONS = [
  { value: 'local', label: 'Local Registry (In-Cluster)', url: 'registry.cr-system.svc.cluster.local:5000' },
  { value: 'quay', label: 'Quay.io', url: 'quay.io' },
  { value: 'dockerhub', label: 'Docker Hub', url: 'docker.io' },
  { value: 'github', label: 'GitHub Container Registry', url: 'ghcr.io' },
];

const DEFAULT_REPO_URL = 'https://github.com/kagenti/agent-examples';
const DEFAULT_BRANCH = 'main';

type DeploymentMethod = 'source' | 'image';

interface EnvVar {
  name: string;
  value: string;
}

interface ServicePort {
  name: string;
  port: number;
  targetPort: number;
  protocol: 'TCP' | 'UDP';
}

export const ImportAgentPage: React.FC = () => {
  const navigate = useNavigate();

  // Deployment method
  const [deploymentMethod, setDeploymentMethod] = useState<DeploymentMethod>('source');

  // Basic info
  const [namespace, setNamespace] = useState('team1');
  const [name, setName] = useState('');
  const [framework, setFramework] = useState('LangGraph');

  // Build from source state
  const [gitUrl, setGitUrl] = useState(DEFAULT_REPO_URL);
  const [gitBranch, setGitBranch] = useState(DEFAULT_BRANCH);
  const [gitPath, setGitPath] = useState('');
  const [selectedExample, setSelectedExample] = useState('');
  const [startCommand, setStartCommand] = useState('python main.py');
  const [showStartCommand, setShowStartCommand] = useState(false);

  // Registry configuration (for build from source)
  const [registryType, setRegistryType] = useState('local');
  const [registryNamespace, setRegistryNamespace] = useState('');
  const [registrySecret, setRegistrySecret] = useState('');

  // Deploy from image state
  const [containerImage, setContainerImage] = useState('');
  const [imageTag, setImageTag] = useState('latest');
  const [imagePullSecret, setImagePullSecret] = useState('');

  // Pod configuration
  const [servicePorts, setServicePorts] = useState<ServicePort[]>([
    { name: 'http', port: 8080, targetPort: 8080, protocol: 'TCP' },
  ]);
  const [showPodConfig, setShowPodConfig] = useState(false);

  // Environment variables
  const [envVars, setEnvVars] = useState<EnvVar[]>([]);
  const [showEnvVars, setShowEnvVars] = useState(false);

  // Validation state
  const [validated, setValidated] = useState<Record<string, 'success' | 'error' | 'default'>>({});

  const createMutation = useMutation({
    mutationFn: (data: Parameters<typeof agentService.create>[0]) =>
      agentService.create(data),
    onSuccess: () => {
      navigate(`/agents/${namespace}/${name || getNameFromPath()}`);
    },
  });

  const getNameFromPath = () => {
    if (deploymentMethod === 'image') {
      // Extract name from image URL
      const parts = containerImage.split('/');
      const imageName = parts[parts.length - 1].split(':')[0];
      return imageName.replace(/_/g, '-').toLowerCase();
    }
    const path = gitPath || selectedExample;
    if (!path) return '';
    const parts = path.split('/');
    return parts[parts.length - 1].replace(/_/g, '-').toLowerCase();
  };

  const handleExampleChange = (value: string) => {
    setSelectedExample(value);
    if (value) {
      setGitPath(value);
      const parts = value.split('/');
      const autoName = parts[parts.length - 1].replace(/_/g, '-').toLowerCase();
      if (!name) {
        setName(autoName);
      }
    }
  };

  const handlePathChange = (value: string) => {
    setGitPath(value);
    setSelectedExample('');
    if (value && !name) {
      const parts = value.split('/');
      const autoName = parts[parts.length - 1].replace(/_/g, '-').toLowerCase();
      setName(autoName);
    }
  };

  const handleImageChange = (value: string) => {
    setContainerImage(value);
    if (value && !name) {
      const parts = value.split('/');
      const imageName = parts[parts.length - 1].split(':')[0];
      setName(imageName.replace(/_/g, '-').toLowerCase());
    }
  };

  // Environment variable handlers
  const addEnvVar = () => {
    setEnvVars([...envVars, { name: '', value: '' }]);
  };

  const removeEnvVar = (index: number) => {
    setEnvVars(envVars.filter((_, i) => i !== index));
  };

  const updateEnvVar = (index: number, field: 'name' | 'value', value: string) => {
    const updated = [...envVars];
    updated[index][field] = value;
    setEnvVars(updated);
  };

  // Service port handlers
  const addServicePort = () => {
    setServicePorts([
      ...servicePorts,
      { name: 'http', port: 8080, targetPort: 8080, protocol: 'TCP' },
    ]);
  };

  const removeServicePort = (index: number) => {
    setServicePorts(servicePorts.filter((_, i) => i !== index));
  };

  const updateServicePort = (index: number, field: keyof ServicePort, value: string | number) => {
    const updated = [...servicePorts];
    if (field === 'port' || field === 'targetPort') {
      updated[index][field] = Number(value);
    } else if (field === 'protocol') {
      updated[index][field] = value as 'TCP' | 'UDP';
    } else {
      updated[index][field] = value as string;
    }
    setServicePorts(updated);
  };

  const getRegistryUrl = () => {
    const registry = REGISTRY_OPTIONS.find((r) => r.value === registryType);
    if (!registry) return '';
    if (registryType === 'local') return registry.url;
    return registryNamespace ? `${registry.url}/${registryNamespace}` : registry.url;
  };

  const validateForm = (): boolean => {
    const newValidated: Record<string, 'success' | 'error' | 'default'> = {};
    let isValid = true;

    // Name validation
    const finalName = name || getNameFromPath();
    if (!finalName) {
      newValidated.name = 'error';
      isValid = false;
    } else if (!/^[a-z0-9][a-z0-9-]*[a-z0-9]$|^[a-z0-9]$/.test(finalName)) {
      newValidated.name = 'error';
      isValid = false;
    } else {
      newValidated.name = 'success';
    }

    if (deploymentMethod === 'source') {
      // Git URL validation
      if (!gitUrl) {
        newValidated.gitUrl = 'error';
        isValid = false;
      } else {
        newValidated.gitUrl = 'success';
      }

      // Git path validation
      if (!gitPath && !selectedExample) {
        newValidated.gitPath = 'error';
        isValid = false;
      } else {
        newValidated.gitPath = 'success';
      }

      // Registry namespace validation for external registries
      if (registryType !== 'local' && !registryNamespace) {
        newValidated.registryNamespace = 'error';
        isValid = false;
      }
    } else {
      // Container image validation
      if (!containerImage) {
        newValidated.containerImage = 'error';
        isValid = false;
      } else {
        newValidated.containerImage = 'success';
      }
    }

    setValidated(newValidated);
    return isValid;
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (!validateForm()) {
      return;
    }

    const finalName = name || getNameFromPath();

    if (deploymentMethod === 'source') {
      const finalPath = gitPath || selectedExample;
      createMutation.mutate({
        name: finalName,
        namespace,
        gitUrl,
        gitPath: finalPath,
        gitBranch,
        imageTag: 'v0.0.1',
        protocol: 'a2a',
        framework,
        envVars: envVars.filter((ev) => ev.name && ev.value),
        // Additional fields for build from source
        deploymentMethod: 'source',
        registryUrl: getRegistryUrl(),
        registrySecret: registryType !== 'local' ? registrySecret : undefined,
        startCommand: showStartCommand ? startCommand : undefined,
        servicePorts: showPodConfig ? servicePorts : undefined,
      });
    } else {
      // Deploy from existing image
      const fullImage = imageTag ? `${containerImage}:${imageTag}` : containerImage;
      createMutation.mutate({
        name: finalName,
        namespace,
        gitUrl: '', // Not used for image deployment
        gitPath: '', // Not used for image deployment
        gitBranch: '',
        imageTag,
        protocol: 'a2a',
        framework,
        envVars: envVars.filter((ev) => ev.name && ev.value),
        // Additional fields for image deployment
        deploymentMethod: 'image',
        containerImage: fullImage,
        imagePullSecret: imagePullSecret || undefined,
        servicePorts: showPodConfig ? servicePorts : undefined,
      });
    }
  };

  return (
    <>
      <PageSection variant="light">
        <TextContent>
          <Title headingLevel="h1">Import New Agent</Title>
          <Text component="p">
            Build from source or deploy an existing container image as an A2A agent.
          </Text>
        </TextContent>
      </PageSection>

      <PageSection>
        <Card>
          <CardTitle>Agent Configuration</CardTitle>
          <CardBody>
            {createMutation.isError && (
              <Alert
                variant="danger"
                title="Failed to create agent"
                isInline
                style={{ marginBottom: '16px' }}
              >
                {createMutation.error instanceof Error
                  ? createMutation.error.message
                  : 'An unexpected error occurred'}
              </Alert>
            )}

            <Form onSubmit={handleSubmit}>
              {/* Basic Information */}
              <FormGroup label="Namespace" isRequired fieldId="namespace">
                <NamespaceSelector
                  namespace={namespace}
                  onNamespaceChange={setNamespace}
                />
                <FormHelperText>
                  <HelperText>
                    <HelperTextItem>
                      The namespace where the agent will be deployed
                    </HelperTextItem>
                  </HelperText>
                </FormHelperText>
              </FormGroup>

              <FormGroup label="Agent Name" fieldId="name" isRequired>
                <TextInput
                  id="name"
                  value={name}
                  onChange={(_e, value) => setName(value)}
                  placeholder="my-agent (auto-generated if empty)"
                  validated={validated.name}
                />
                <FormHelperText>
                  <HelperText>
                    <HelperTextItem variant={validated.name === 'error' ? 'error' : 'default'}>
                      {validated.name === 'error'
                        ? 'Name must be lowercase alphanumeric with hyphens'
                        : 'Leave empty to auto-generate from source path or image name'}
                    </HelperTextItem>
                  </HelperText>
                </FormHelperText>
              </FormGroup>

              <Divider style={{ margin: '24px 0' }} />

              {/* Deployment Method Selection */}
              <Title headingLevel="h3" size="md" style={{ marginBottom: '16px' }}>
                Deployment Method
              </Title>

              <FormGroup role="radiogroup" fieldId="deployment-method">
                <Radio
                  id="method-source"
                  name="deployment-method"
                  label="Build from Source"
                  description="Build container image from a git repository"
                  isChecked={deploymentMethod === 'source'}
                  onChange={() => setDeploymentMethod('source')}
                />
                <Radio
                  id="method-image"
                  name="deployment-method"
                  label="Deploy from Existing Image"
                  description="Deploy using an existing container image"
                  isChecked={deploymentMethod === 'image'}
                  onChange={() => setDeploymentMethod('image')}
                  style={{ marginTop: '8px' }}
                />
              </FormGroup>

              <Divider style={{ margin: '24px 0' }} />

              {/* Build from Source Configuration */}
              {deploymentMethod === 'source' && (
                <>
                  <Title headingLevel="h3" size="md" style={{ marginBottom: '16px' }}>
                    Source Repository
                  </Title>

                  <FormGroup label="Git Repository URL" isRequired fieldId="gitUrl">
                    <TextInput
                      id="gitUrl"
                      value={gitUrl}
                      onChange={(_e, value) => setGitUrl(value)}
                      placeholder="https://github.com/org/repo"
                      validated={validated.gitUrl}
                    />
                  </FormGroup>

                  <FormGroup label="Git Branch" fieldId="gitBranch">
                    <TextInput
                      id="gitBranch"
                      value={gitBranch}
                      onChange={(_e, value) => setGitBranch(value)}
                      placeholder="main"
                    />
                  </FormGroup>

                  <FormGroup label="Select Example" fieldId="example">
                    <FormSelect
                      id="example"
                      value={selectedExample}
                      onChange={(_e, value) => handleExampleChange(value)}
                    >
                      {AGENT_EXAMPLES.map((ex) => (
                        <FormSelectOption key={ex.value} value={ex.value} label={ex.label} />
                      ))}
                    </FormSelect>
                    <FormHelperText>
                      <HelperText>
                        <HelperTextItem>Or enter a custom path below</HelperTextItem>
                      </HelperText>
                    </FormHelperText>
                  </FormGroup>

                  <FormGroup label="Source Path" isRequired fieldId="gitPath">
                    <TextInput
                      id="gitPath"
                      value={gitPath}
                      onChange={(_e, value) => handlePathChange(value)}
                      placeholder="path/to/agent"
                      validated={validated.gitPath}
                    />
                    <FormHelperText>
                      <HelperText>
                        <HelperTextItem variant={validated.gitPath === 'error' ? 'error' : 'default'}>
                          {validated.gitPath === 'error'
                            ? 'Source path is required'
                            : 'Path to agent source within the repository'}
                        </HelperTextItem>
                      </HelperText>
                    </FormHelperText>
                  </FormGroup>

                  <Divider style={{ margin: '24px 0' }} />

                  {/* Container Registry Configuration */}
                  <Title headingLevel="h3" size="md" style={{ marginBottom: '16px' }}>
                    Container Registry Configuration
                  </Title>

                  <FormGroup label="Container Registry" fieldId="registryType">
                    <FormSelect
                      id="registryType"
                      value={registryType}
                      onChange={(_e, value) => setRegistryType(value)}
                    >
                      {REGISTRY_OPTIONS.map((reg) => (
                        <FormSelectOption key={reg.value} value={reg.value} label={reg.label} />
                      ))}
                    </FormSelect>
                    <FormHelperText>
                      <HelperText>
                        <HelperTextItem>
                          Where the built container image will be pushed
                        </HelperTextItem>
                      </HelperText>
                    </FormHelperText>
                  </FormGroup>

                  {registryType !== 'local' && (
                    <>
                      <FormGroup
                        label="Registry Namespace/Organization"
                        isRequired
                        fieldId="registryNamespace"
                      >
                        <TextInput
                          id="registryNamespace"
                          value={registryNamespace}
                          onChange={(_e, value) => setRegistryNamespace(value)}
                          placeholder="your-org-name"
                          validated={validated.registryNamespace}
                        />
                        <FormHelperText>
                          <HelperText>
                            <HelperTextItem>
                              Your organization or namespace in the registry
                            </HelperTextItem>
                          </HelperText>
                        </FormHelperText>
                      </FormGroup>

                      <FormGroup label="Registry Secret Name" fieldId="registrySecret">
                        <TextInput
                          id="registrySecret"
                          value={registrySecret}
                          onChange={(_e, value) => setRegistrySecret(value)}
                          placeholder={`${registryType}-registry-secret`}
                        />
                        <FormHelperText>
                          <HelperText>
                            <HelperTextItem>
                              Kubernetes secret containing registry credentials
                            </HelperTextItem>
                          </HelperText>
                        </FormHelperText>
                      </FormGroup>

                      <Alert
                        variant="info"
                        title="Authentication Required"
                        isInline
                        style={{ marginBottom: '16px' }}
                      >
                        Ensure the registry secret exists in the target namespace with push credentials.
                      </Alert>
                    </>
                  )}

                  {/* Start Command Override */}
                  <ExpandableSection
                    toggleText="Override Start Command"
                    isExpanded={showStartCommand}
                    onToggle={() => setShowStartCommand(!showStartCommand)}
                  >
                    <FormGroup label="Start Command" fieldId="startCommand">
                      <TextInput
                        id="startCommand"
                        value={startCommand}
                        onChange={(_e, value) => setStartCommand(value)}
                        placeholder="python main.py"
                      />
                      <FormHelperText>
                        <HelperText>
                          <HelperTextItem>
                            Command to start the agent (e.g., "python main.py", "uvicorn app:app")
                          </HelperTextItem>
                        </HelperText>
                      </FormHelperText>
                    </FormGroup>
                  </ExpandableSection>
                </>
              )}

              {/* Deploy from Existing Image Configuration */}
              {deploymentMethod === 'image' && (
                <>
                  <Title headingLevel="h3" size="md" style={{ marginBottom: '16px' }}>
                    Container Image
                  </Title>

                  <FormGroup label="Container Image" isRequired fieldId="containerImage">
                    <TextInput
                      id="containerImage"
                      value={containerImage}
                      onChange={(_e, value) => handleImageChange(value)}
                      placeholder="myrepo/my-agent"
                      validated={validated.containerImage}
                    />
                    <FormHelperText>
                      <HelperText>
                        <HelperTextItem variant={validated.containerImage === 'error' ? 'error' : 'default'}>
                          {validated.containerImage === 'error'
                            ? 'Container image is required'
                            : 'Full image path without tag (e.g., quay.io/myorg/my-agent)'}
                        </HelperTextItem>
                      </HelperText>
                    </FormHelperText>
                  </FormGroup>

                  <FormGroup label="Image Tag" fieldId="imageTag">
                    <TextInput
                      id="imageTag"
                      value={imageTag}
                      onChange={(_e, value) => setImageTag(value)}
                      placeholder="latest"
                    />
                  </FormGroup>

                  <FormGroup label="Image Pull Secret" fieldId="imagePullSecret">
                    <TextInput
                      id="imagePullSecret"
                      value={imagePullSecret}
                      onChange={(_e, value) => setImagePullSecret(value)}
                      placeholder="Leave empty for public images"
                    />
                    <FormHelperText>
                      <HelperText>
                        <HelperTextItem>
                          Kubernetes secret containing credentials for private registries
                        </HelperTextItem>
                      </HelperText>
                    </FormHelperText>
                  </FormGroup>
                </>
              )}

              <Divider style={{ margin: '24px 0' }} />

              {/* Framework Selection */}
              <FormGroup label="Framework" fieldId="framework">
                <FormSelect
                  id="framework"
                  value={framework}
                  onChange={(_e, value) => setFramework(value)}
                >
                  {FRAMEWORKS.map((fw) => (
                    <FormSelectOption key={fw.value} value={fw.value} label={fw.label} />
                  ))}
                </FormSelect>
              </FormGroup>

              {/* Pod Configuration */}
              <ExpandableSection
                toggleText={`Pod Configuration (${servicePorts.length} port${servicePorts.length !== 1 ? 's' : ''})`}
                isExpanded={showPodConfig}
                onToggle={() => setShowPodConfig(!showPodConfig)}
              >
                <Card isFlat style={{ marginTop: '8px' }}>
                  <CardBody>
                    <Text component="p" style={{ marginBottom: '16px' }}>
                      Configure service ports for the agent pod.
                    </Text>

                    {servicePorts.map((port, index) => (
                      <Grid hasGutter key={index} style={{ marginBottom: '8px' }}>
                        <GridItem span={3}>
                          <TextInput
                            aria-label="Port name"
                            value={port.name}
                            onChange={(_e, value) => updateServicePort(index, 'name', value)}
                            placeholder="http"
                          />
                          {index === 0 && (
                            <FormHelperText>
                              <HelperText>
                                <HelperTextItem>Port Name</HelperTextItem>
                              </HelperText>
                            </FormHelperText>
                          )}
                        </GridItem>
                        <GridItem span={2}>
                          <NumberInput
                            value={port.port}
                            min={1}
                            max={65535}
                            onMinus={() => updateServicePort(index, 'port', port.port - 1)}
                            onPlus={() => updateServicePort(index, 'port', port.port + 1)}
                            onChange={(event) => {
                              const target = event.target as HTMLInputElement;
                              updateServicePort(index, 'port', parseInt(target.value, 10) || 8080);
                            }}
                            inputAriaLabel="Service port"
                          />
                          {index === 0 && (
                            <FormHelperText>
                              <HelperText>
                                <HelperTextItem>Service Port</HelperTextItem>
                              </HelperText>
                            </FormHelperText>
                          )}
                        </GridItem>
                        <GridItem span={2}>
                          <NumberInput
                            value={port.targetPort}
                            min={1}
                            max={65535}
                            onMinus={() => updateServicePort(index, 'targetPort', port.targetPort - 1)}
                            onPlus={() => updateServicePort(index, 'targetPort', port.targetPort + 1)}
                            onChange={(event) => {
                              const target = event.target as HTMLInputElement;
                              updateServicePort(index, 'targetPort', parseInt(target.value, 10) || 8080);
                            }}
                            inputAriaLabel="Target port"
                          />
                          {index === 0 && (
                            <FormHelperText>
                              <HelperText>
                                <HelperTextItem>Target Port</HelperTextItem>
                              </HelperText>
                            </FormHelperText>
                          )}
                        </GridItem>
                        <GridItem span={2}>
                          <FormSelect
                            value={port.protocol}
                            onChange={(_e, value) => updateServicePort(index, 'protocol', value)}
                            aria-label="Protocol"
                          >
                            <FormSelectOption value="TCP" label="TCP" />
                            <FormSelectOption value="UDP" label="UDP" />
                          </FormSelect>
                          {index === 0 && (
                            <FormHelperText>
                              <HelperText>
                                <HelperTextItem>Protocol</HelperTextItem>
                              </HelperText>
                            </FormHelperText>
                          )}
                        </GridItem>
                        <GridItem span={1}>
                          <Button
                            variant="plain"
                            onClick={() => removeServicePort(index)}
                            aria-label="Remove port"
                            isDisabled={servicePorts.length <= 1}
                          >
                            <TrashIcon />
                          </Button>
                        </GridItem>
                      </Grid>
                    ))}

                    <Button
                      variant="link"
                      icon={<PlusCircleIcon />}
                      onClick={addServicePort}
                    >
                      Add Service Port
                    </Button>
                  </CardBody>
                </Card>
              </ExpandableSection>

              {/* Environment Variables */}
              <ExpandableSection
                toggleText={`Environment Variables (${envVars.length})`}
                isExpanded={showEnvVars}
                onToggle={() => setShowEnvVars(!showEnvVars)}
              >
                <Card isFlat style={{ marginTop: '8px' }}>
                  <CardBody>
                    {envVars.map((env, index) => (
                      <Split hasGutter key={index} style={{ marginBottom: '8px' }}>
                        <SplitItem isFilled>
                          <TextInput
                            aria-label="Environment variable name"
                            value={env.name}
                            onChange={(_e, value) => updateEnvVar(index, 'name', value)}
                            placeholder="VAR_NAME"
                          />
                        </SplitItem>
                        <SplitItem isFilled>
                          <TextInput
                            aria-label="Environment variable value"
                            value={env.value}
                            onChange={(_e, value) => updateEnvVar(index, 'value', value)}
                            placeholder="value"
                          />
                        </SplitItem>
                        <SplitItem>
                          <Button
                            variant="plain"
                            onClick={() => removeEnvVar(index)}
                            aria-label="Remove environment variable"
                          >
                            <TrashIcon />
                          </Button>
                        </SplitItem>
                      </Split>
                    ))}
                    <Button
                      variant="link"
                      icon={<PlusCircleIcon />}
                      onClick={addEnvVar}
                    >
                      Add Environment Variable
                    </Button>
                  </CardBody>
                </Card>
              </ExpandableSection>

              <ActionGroup style={{ marginTop: '24px' }}>
                <Button
                  variant="primary"
                  type="submit"
                  isLoading={createMutation.isPending}
                  isDisabled={createMutation.isPending}
                >
                  {createMutation.isPending
                    ? 'Creating...'
                    : deploymentMethod === 'source'
                      ? 'Build & Deploy Agent'
                      : 'Deploy Agent'}
                </Button>
                <Button variant="link" onClick={() => navigate('/agents')}>
                  Cancel
                </Button>
              </ActionGroup>
            </Form>
          </CardBody>
        </Card>

        {/* Developer Resources */}
        <Alert
          variant="info"
          title="Agent Developer Resources"
          isInline
          style={{ marginTop: '24px' }}
        >
          New to agent development? Check our{' '}
          <a
            href="https://github.com/kagenti/kagenti/blob/main/PERSONAS_AND_ROLES.md#11-agent-developer"
            target="_blank"
            rel="noopener noreferrer"
          >
            Agent Developer guide
          </a>{' '}
          and{' '}
          <a
            href="https://github.com/kagenti/agent-examples"
            target="_blank"
            rel="noopener noreferrer"
          >
            agent-examples repository
          </a>
          .
        </Alert>
      </PageSection>
    </>
  );
};
