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
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
            </cv-toggle>
            <cv-toggle
              value="http2https"
              :label="$t('settings.http2https')"
              v-model="http2https"
              :disabled="loading.getConfiguration || loading.configureModule"
              class="toggle"
            >
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
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
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
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
              <template slot="text-left">{{
                $t("settings.disabled")
              }}</template>
              <template slot="text-right">{{
                $t("settings.enabled")
              }}</template>
            </cv-toggle>
            <template v-if="ldap_enabled">
              <cv-text-input
                :label="$t('settings.ldap_title')"
                v-model.trim="ldap_title"
                :helper-text="$t('settings.ldap_title_helper')"
                :invalid-message="error.ldap_title"
                :disabled="loading.getConfiguration || loading.configureModule"
                ref="ldap_title"
                class="spaced"
              ></cv-text-input>
              <LdapLogin
                v-model="ldap"
                :userDomains="user_domains"
                :bindPasswordSet="ldap_bind_password_set"
                :errors="ldapErrors"
                :disabled="loading.getConfiguration || loading.configureModule"
                ref="ldap"
              />
              <NsInlineNotification
                v-for="msg in ldapChoiceErrors"
                :key="msg"
                kind="error"
                :title="msg"
                :showCloseButton="false"
                class="info-tile"
              />
              <NsInlineNotification
                kind="info"
                :title="$t('settings.ldap_limits_title')"
                :description="$t('settings.ldap_limits')"
                :showCloseButton="false"
                class="info-tile"
              />
            </template>

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
import LdapLogin, {
  LDAP_FIELDS,
  ldapFromConfiguration,
  validateLdap,
} from "@/components/LdapLogin";

export default {
  name: "Settings",
  components: { LdapLogin },
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
      ldap_title: "AD",
      ldap: ldapFromConfiguration({}),
      ldap_bind_password_set: false,
      user_domains: [],
      ldapErrors: {},
      loading: {
        getConfiguration: false,
        configureModule: false,
      },
      error: {
        getConfiguration: "",
        configureModule: "",
        host: "",
        ldap_title: "",
      },
    };
  },
  computed: {
    ...mapState(["instanceName", "core", "appName"]),
    ldapChoiceErrors() {
      // LdapLogin shows messages only below its text fields: errors of its
      // toggles and radio groups (e.g. StartTLS) are shown here
      return ["ldap_source", "ldap_start_tls", "ldap_tls_verify", "ldap_schema"]
        .filter((f) => this.ldapErrors[f])
        .map((f) => this.$t(this.ldapErrors[f]));
    },
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
      this.ldap_title = config.ldap_title || "AD";
      this.user_domains = config.user_domains || [];
      this.ldap = ldapFromConfiguration(config);
      this.ldap_bind_password_set = !!config.ldap_bind_password_set;
      this.focusElement("host");
    },
    validateConfigureModule() {
      this.clearErrors(this);
      this.ldapErrors = {};
      let isValidationOk = true;
      if (!this.host) {
        this.error.host = "common.required";
        this.focusElement("host");
        isValidationOk = false;
      }
      if (this.ldap_enabled) {
        const ldapErrors = validateLdap(this.ldap, this.ldap_bind_password_set);
        if (this.ldap.ldap_source === "custom" && this.ldap.ldap_start_tls)
          ldapErrors.push(["ldap_start_tls", "settings.start_tls_unsupported"]);
        for (const [field, msg] of ldapErrors)
          this.$set(this.ldapErrors, field, msg);
        if (ldapErrors.length && isValidationOk)
          this.$refs.ldap.focus(ldapErrors[0][0]);
        if (ldapErrors.length) isValidationOk = false;
      }
      return isValidationOk;
    },
    configureModuleValidationFailed(validationErrors) {
      this.loading.configureModule = false;
      let focusAlreadySet = false;
      for (const validationError of validationErrors) {
        const field = validationError.field;
        if (LDAP_FIELDS.includes(field)) {
          // shared messages under ldap_login, ARSnova limits under settings
          const key = this.$te("ldap_login." + validationError.error)
            ? "ldap_login." + validationError.error
            : "settings." + validationError.error;
          this.$set(this.ldapErrors, field, key);
          if (!focusAlreadySet && this.$refs.ldap) {
            this.$refs.ldap.focus(field);
            focusAlreadySet = true;
          }
        } else if (field !== "(root)") {
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
            ldap_title: this.ldap_title,
            ...this.ldap,
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
