<!--
  Copyright (C) 2026 tebbi
  SPDX-License-Identifier: GPL-3.0-or-later
-->
<template>
  <cv-grid fullWidth>
    <cv-row>
      <cv-column class="page-title">
        <h2>{{ $t("settings.title") }}</h2>
      </cv-column>
    </cv-row>
    <cv-row v-if="error.getConfiguration">
      <cv-column>
        <NsInlineNotification
          kind="error"
          :title="$t('action.get-configuration')"
          :description="error.getConfiguration"
          :showCloseButton="false"
        />
      </cv-column>
    </cv-row>
    <cv-row>
      <cv-column>
        <cv-tile light>
          <cv-form @submit.prevent="configureModule">
            <cv-text-input
              :label="$t('settings.host')"
              v-model.trim="host"
              :placeholder="$t('settings.host_placeholder')"
              :helper-text="$t('settings.host_helper')"
              :disabled="loading.getConfiguration || loading.configureModule"
              :invalid-message="$t(error.host)"
              ref="host"
            ></cv-text-input>
            <cv-toggle
              value="lets_encrypt"
              :label="$t('settings.lets_encrypt')"
              v-model="lets_encrypt"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="toggle"
            >
              <template slot="text-left">{{ $t("settings.disabled") }}</template>
              <template slot="text-right">{{ $t("settings.enabled") }}</template>
            </cv-toggle>
            <cv-toggle
              value="http2https"
              :label="$t('settings.http2https')"
              v-model="http2https"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="toggle"
            >
              <template slot="text-left">{{ $t("settings.disabled") }}</template>
              <template slot="text-right">{{ $t("settings.enabled") }}</template>
            </cv-toggle>
            <NsInlineNotification
              kind="info"
              :title="$t('settings.http2https')"
              :description="$t('settings.https_hint')"
              :showCloseButton="false"
              class="info-tile"
            />
            <cv-text-input
              :label="$t('settings.admin_email')"
              v-model.trim="admin_email"
              :placeholder="$t('settings.admin_email_placeholder')"
              :helper-text="$t('settings.admin_email_helper')"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="spaced"
            ></cv-text-input>
            <cv-toggle
              value="allow_registration"
              :label="$t('settings.allow_registration')"
              v-model="allow_registration"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="toggle"
            >
              <template slot="text-left">{{ $t("settings.disabled") }}</template>
              <template slot="text-right">{{ $t("settings.enabled") }}</template>
            </cv-toggle>
            <NsInlineNotification
              v-if="!allow_registration"
              kind="info"
              :title="$t('settings.allow_registration')"
              :description="$t('settings.allow_registration_off_hint')"
              :showCloseButton="false"
              class="info-tile"
            />

            <h4 class="section">{{ $t("settings.mail_section") }}</h4>
            <cv-text-input
              :label="$t('settings.smtp_host')"
              v-model.trim="smtp_host"
              :helper-text="$t('settings.smtp_host_helper')"
              :disabled="loading.getConfiguration || loading.configureModule"
            ></cv-text-input>
            <cv-text-input
              :label="$t('settings.smtp_from')"
              v-model.trim="smtp_from"
              :placeholder="$t('settings.smtp_from_placeholder')"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="spaced"
            ></cv-text-input>

            <NsInlineNotification
              v-if="public_url"
              kind="info"
              :title="$t('settings.public_url')"
              :description="$t('settings.public_url_desc', { url: public_url })"
              :showCloseButton="false"
              class="info-tile"
            />

            <h4 class="section">{{ $t("settings.ldap_section") }}</h4>
            <cv-toggle
              value="ldap_enabled"
              :label="$t('settings.ldap_enabled')"
              v-model="ldap_enabled"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="toggle"
            >
              <template slot="text-left">{{ $t("settings.disabled") }}</template>
              <template slot="text-right">{{ $t("settings.enabled") }}</template>
            </cv-toggle>
            <div v-if="ldap_enabled">
              <cv-text-input
                :label="$t('settings.ldap_url')"
                v-model.trim="ldap_url"
                placeholder="ldaps://ad.example.org:636"
                :disabled="loading.getConfiguration || loading.configureModule"
                class="spaced"
              ></cv-text-input>
              <cv-text-input
                :label="$t('settings.ldap_base_dn')"
                v-model.trim="ldap_base_dn"
                placeholder="DC=ad,DC=example,DC=org"
                :disabled="loading.getConfiguration || loading.configureModule"
                class="spaced"
              ></cv-text-input>
              <cv-text-input
                :label="$t('settings.ldap_bind_dn')"
                v-model.trim="ldap_bind_dn"
                placeholder="ldapservice@ad.example.org"
                :disabled="loading.getConfiguration || loading.configureModule"
                class="spaced"
              ></cv-text-input>
              <cv-text-input
                type="password"
                :label="$t('settings.ldap_bind_password')"
                v-model="ldap_bind_password"
                :disabled="loading.getConfiguration || loading.configureModule"
                class="spaced"
              ></cv-text-input>
              <cv-text-input
                :label="$t('settings.ldap_user_attribute')"
                v-model.trim="ldap_user_attribute"
                placeholder="sAMAccountName"
                :disabled="loading.getConfiguration || loading.configureModule"
                class="spaced"
              ></cv-text-input>
              <div class="spaced">
                <NsButton
                  kind="tertiary"
                  size="small"
                  :loading="loading.listLdapGroups"
                  :disabled="loading.listLdapGroups || !ldap_url || !ldap_bind_dn"
                  @click.prevent="loadLdapGroups"
                  >{{ $t("settings.ldap_load_groups") }}</NsButton
                >
              </div>
              <cv-dropdown
                v-if="ldapGroups.length"
                :label="$t('settings.ldap_group')"
                v-model="ldap_group"
                :disabled="loading.getConfiguration || loading.configureModule"
                class="spaced"
              >
                <cv-dropdown-item value="">{{
                  $t("settings.ldap_group_any")
                }}</cv-dropdown-item>
                <cv-dropdown-item
                  v-for="g in ldapGroups"
                  :key="g.dn"
                  :value="g.dn"
                  >{{ g.name }}</cv-dropdown-item
                >
              </cv-dropdown>
              <cv-text-input
                v-else
                :label="$t('settings.ldap_group')"
                v-model.trim="ldap_group"
                :helper-text="$t('settings.ldap_group_helper')"
                :disabled="loading.getConfiguration || loading.configureModule"
                class="spaced"
              ></cv-text-input>
              <NsInlineNotification
                v-if="error.listLdapGroups"
                kind="warning"
                :title="$t('settings.ldap_load_groups')"
                :description="error.listLdapGroups"
                :showCloseButton="false"
                class="info-tile"
              />
            </div>

            <cv-row v-if="error.configureModule">
              <cv-column>
                <NsInlineNotification
                  kind="error"
                  :title="$t('action.configure-module')"
                  :description="error.configureModule"
                  :showCloseButton="false"
                />
              </cv-column>
            </cv-row>
            <NsButton
              kind="primary"
              :icon="Save20"
              :loading="loading.configureModule"
              :disabled="loading.getConfiguration || loading.configureModule"
              >{{ $t("settings.save") }}</NsButton
            >
          </cv-form>
        </cv-tile>
      </cv-column>
    </cv-row>
  </cv-grid>
</template>

<script>
import to from "await-to-js";
import { mapState } from "vuex";
import {
  QueryParamService,
  UtilService,
  TaskService,
  IconService,
  PageTitleService,
} from "@nethserver/ns8-ui-lib";

export default {
  name: "Settings",
  mixins: [
    TaskService,
    IconService,
    UtilService,
    QueryParamService,
    PageTitleService,
  ],
  pageTitle() {
    return this.$t("settings.title") + " - " + this.appName;
  },
  data() {
    return {
      q: {
        page: "settings",
      },
      urlCheckInterval: null,
      host: "",
      lets_encrypt: false,
      http2https: false,
      admin_email: "",
      allow_registration: true,
      smtp_host: "",
      smtp_from: "",
      public_url: "",
      ldap_enabled: false,
      ldap_url: "",
      ldap_base_dn: "",
      ldap_bind_dn: "",
      ldap_bind_password: "",
      ldap_user_attribute: "sAMAccountName",
      ldap_title: "AD",
      ldap_group: "",
      ldapGroups: [],
      loading: {
        getConfiguration: false,
        configureModule: false,
        listLdapGroups: false,
      },
      error: {
        getConfiguration: "",
        configureModule: "",
        listLdapGroups: "",
        host: "",
      },
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
  },
  beforeRouteEnter(to, from, next) {
    next((vm) => {
      vm.watchQueryData(vm);
      vm.urlCheckInterval = vm.initUrlBindingForApp(vm, vm.q.page);
    });
  },
  beforeRouteLeave(to, from, next) {
    clearInterval(this.urlCheckInterval);
    next();
  },
  created() {
    this.getConfiguration();
  },
  methods: {
    async getConfiguration() {
      this.loading.getConfiguration = true;
      this.error.getConfiguration = "";
      const taskAction = "get-configuration";
      const eventId = this.getUuid();

      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.getConfigurationAborted
      );
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.getConfigurationCompleted
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          extra: {
            title: this.$t("action." + taskAction),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      const err = res[0];
      if (err) {
        this.error.getConfiguration = this.getErrorMessage(err);
        this.loading.getConfiguration = false;
      }
    },
    getConfigurationAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.getConfiguration = this.$t("error.generic_error");
      this.loading.getConfiguration = false;
    },
    getConfigurationCompleted(taskContext, taskResult) {
      this.loading.getConfiguration = false;
      const config = taskResult.output;
      this.host = config.host || "";
      this.lets_encrypt = !!config.lets_encrypt;
      this.http2https = !!config.http2https;
      this.admin_email = config.admin_email || "";
      this.allow_registration = config.allow_registration !== false;
      this.smtp_host = config.smtp_host || "";
      this.smtp_from = config.smtp_from || "";
      this.public_url = config.public_url || "";
      this.ldap_enabled = !!config.ldap_enabled;
      this.ldap_url = config.ldap_url || "";
      this.ldap_base_dn = config.ldap_base_dn || "";
      this.ldap_bind_dn = config.ldap_bind_dn || "";
      this.ldap_bind_password = config.ldap_bind_password || "";
      this.ldap_user_attribute = config.ldap_user_attribute || "sAMAccountName";
      this.ldap_title = config.ldap_title || "AD";
      this.ldap_group = config.ldap_group || "";
      this.focusElement("host");
    },
    async loadLdapGroups() {
      this.loading.listLdapGroups = true;
      this.error.listLdapGroups = "";
      const taskAction = "list-ldap-groups";
      const eventId = this.getUuid();
      this.core.$root.$once(`${taskAction}-aborted-${eventId}`, (tr) => {
        console.error(`${taskAction} aborted`, tr);
        this.error.listLdapGroups = this.$t("error.generic_error");
        this.loading.listLdapGroups = false;
      });
      this.core.$root.$once(`${taskAction}-completed-${eventId}`, (tc, tr) => {
        this.loading.listLdapGroups = false;
        const out = tr.output || {};
        if (out.error) {
          this.error.listLdapGroups = out.error;
        }
        this.ldapGroups = out.groups || [];
      });
      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data: {
            ldap_url: this.ldap_url,
            ldap_base_dn: this.ldap_base_dn,
            ldap_bind_dn: this.ldap_bind_dn,
            ldap_bind_password: this.ldap_bind_password,
          },
          extra: {
            title: this.$t("settings.ldap_load_groups"),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      if (res[0]) {
        this.error.listLdapGroups = this.getErrorMessage(res[0]);
        this.loading.listLdapGroups = false;
      }
    },
    validateConfigureModule() {
      this.clearErrors(this);
      let isValidationOk = true;
      if (!this.host) {
        this.error.host = "common.required";
        this.focusElement("host");
        isValidationOk = false;
      }
      return isValidationOk;
    },
    configureModuleValidationFailed(validationErrors) {
      this.loading.configureModule = false;
      let focusAlreadySet = false;
      for (const validationError of validationErrors) {
        const field = validationError.field;
        if (field !== "(root)") {
          this.error[field] = this.$t("settings." + validationError.error);
          if (!focusAlreadySet) {
            this.focusElement(field);
            focusAlreadySet = true;
          }
        }
      }
    },
    async configureModule() {
      if (!this.validateConfigureModule()) {
        return;
      }
      this.loading.configureModule = true;
      const taskAction = "configure-module";
      const eventId = this.getUuid();

      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        this.configureModuleAborted
      );
      this.core.$root.$once(
        `${taskAction}-validation-failed-${eventId}`,
        this.configureModuleValidationFailed
      );
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        this.configureModuleCompleted
      );

      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data: {
            host: this.host,
            lets_encrypt: this.lets_encrypt,
            http2https: this.http2https,
            admin_email: this.admin_email,
            allow_registration: this.allow_registration,
            smtp_host: this.smtp_host,
            smtp_from: this.smtp_from,
            ldap_enabled: this.ldap_enabled,
            ldap_url: this.ldap_url,
            ldap_base_dn: this.ldap_base_dn,
            ldap_bind_dn: this.ldap_bind_dn,
            ldap_bind_password: this.ldap_bind_password,
            ldap_user_attribute: this.ldap_user_attribute,
            ldap_title: this.ldap_title,
            ldap_group: this.ldap_group,
          },
          extra: {
            title: this.$t("settings.configure_instance", {
              instance: this.instanceName,
            }),
            description: this.$t("common.processing"),
            eventId,
          },
        })
      );
      const err = res[0];
      if (err) {
        this.error.configureModule = this.getErrorMessage(err);
        this.loading.configureModule = false;
      }
    },
    configureModuleAborted(taskResult, taskContext) {
      console.error(`${taskContext.action} aborted`, taskResult);
      this.error.configureModule = this.$t("error.generic_error");
      this.loading.configureModule = false;
    },
    configureModuleCompleted() {
      this.loading.configureModule = false;
      this.getConfiguration();
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";
.toggle {
  margin-top: $spacing-06;
}
.info-tile {
  margin-top: $spacing-06;
}
.spaced {
  margin-top: $spacing-06;
}
.section {
  margin-top: $spacing-07;
  margin-bottom: $spacing-03;
}
</style>
