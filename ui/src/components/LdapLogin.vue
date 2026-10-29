<!--
  Copyright (C) 2026 tebbi
  SPDX-License-Identifier: GPL-3.0-or-later

  Directory login settings shared by the tebbiworld NS8 modules (kept
  identical in ns8-clamav and ns8-idevice-backup, ui/src/components; here
  the radio group headings are labels, cv-radio-group shows no legend). The
  parent owns the values: v-model with an object of the ldap_* fields of
  configure-module; translations under "ldap_login".
-->
<template>
  <div class="ldap-login">
    <div class="bx--label field">{{ $t("ldap_login.source") }}</div>
    <cv-radio-group vertical>
      <cv-radio-button
        :name="'ldap_source_' + uid"
        value="domain"
        :checked="value.ldap_source === 'domain'"
        :label="$t('ldap_login.source_domain')"
        :disabled="disabled || !userDomains.length"
        @change="set('ldap_source', 'domain')"
      />
      <cv-radio-button
        :name="'ldap_source_' + uid"
        value="custom"
        :checked="value.ldap_source === 'custom'"
        :label="$t('ldap_login.source_custom')"
        :disabled="disabled"
        @change="set('ldap_source', 'custom')"
      />
    </cv-radio-group>
    <p v-if="!userDomains.length" class="ldap-note">
      {{ $t("ldap_login.no_domains") }}
    </p>

    <template v-if="value.ldap_source === 'domain'">
      <cv-dropdown
        :label="$t('ldap_login.domain')"
        :value="value.ldap_domain"
        :invalid-message="errorText('ldap_domain')"
        :disabled="disabled"
        ref="ldap_domain"
        class="field"
        @change="setDomain"
      >
        <cv-dropdown-item v-for="d in userDomains" :key="d" :value="d">{{
          d
        }}</cv-dropdown-item>
      </cv-dropdown>
      <NsComboBox
        :key="'groups-' + value.ldap_domain + '-' + groups.length"
        :title="$t('ldap_login.group')"
        :label="
          loadingGroups
            ? $t('ldap_login.loading_groups')
            : $t('ldap_login.group_placeholder')
        "
        :options="groupOptions"
        :value="value.ldap_group"
        :auto-filter="true"
        :auto-highlight="true"
        :accept-user-input="true"
        :helper-text="$t('ldap_login.group_helper')"
        :invalid-message="errorText('ldap_group')"
        :disabled="disabled || loadingGroups"
        ref="ldap_group"
        class="field"
        @change="set('ldap_group', $event || '')"
      />
    </template>

    <template v-else>
      <p class="ldap-note">{{ $t("ldap_login.custom_intro") }}</p>
      <cv-text-input
        :label="$t('ldap_login.url')"
        :value="value.ldap_url"
        placeholder="ldaps://dc.example.org:636"
        :helper-text="$t('ldap_login.url_helper')"
        :invalid-message="errorText('ldap_url')"
        :disabled="disabled"
        ref="ldap_url"
        class="field"
        @input="set('ldap_url', $event.trim())"
      />
      <cv-toggle
        :value="'ldap_start_tls_' + uid"
        :label="$t('ldap_login.start_tls')"
        :checked="value.ldap_start_tls"
        :disabled="disabled || isLdaps"
        class="field"
        @change="set('ldap_start_tls', $event)"
      >
        <template slot="text-left">{{ $t("common.disabled") }}</template>
        <template slot="text-right">{{ $t("common.enabled") }}</template>
      </cv-toggle>
      <cv-toggle
        :value="'ldap_tls_verify_' + uid"
        :label="$t('ldap_login.tls_verify')"
        :checked="value.ldap_tls_verify"
        :disabled="disabled"
        class="field"
        @change="set('ldap_tls_verify', $event)"
      >
        <template slot="text-left">{{ $t("common.disabled") }}</template>
        <template slot="text-right">{{ $t("common.enabled") }}</template>
      </cv-toggle>
      <NsInlineNotification
        v-if="!value.ldap_tls_verify"
        kind="warning"
        :title="$t('ldap_login.tls_verify_off')"
        :showCloseButton="false"
        class="field"
      />
      <div class="bx--label field">{{ $t("ldap_login.schema") }}</div>
      <cv-radio-group>
        <cv-radio-button
          :name="'ldap_schema_' + uid"
          value="ad"
          :checked="value.ldap_schema !== 'rfc2307'"
          :label="$t('ldap_login.schema_ad')"
          :disabled="disabled"
          @change="set('ldap_schema', 'ad')"
        />
        <cv-radio-button
          :name="'ldap_schema_' + uid"
          value="rfc2307"
          :checked="value.ldap_schema === 'rfc2307'"
          :label="$t('ldap_login.schema_rfc2307')"
          :disabled="disabled"
          @change="set('ldap_schema', 'rfc2307')"
        />
      </cv-radio-group>
      <cv-text-input
        :label="$t('ldap_login.base_dn')"
        :value="value.ldap_base_dn"
        placeholder="DC=example,DC=org"
        :invalid-message="errorText('ldap_base_dn')"
        :disabled="disabled"
        ref="ldap_base_dn"
        class="field"
        @input="set('ldap_base_dn', $event.trim())"
      />
      <cv-text-input
        :label="$t('ldap_login.bind_dn')"
        :value="value.ldap_bind_dn"
        placeholder="CN=svc-login,CN=Users,DC=example,DC=org"
        :invalid-message="errorText('ldap_bind_dn')"
        :disabled="disabled"
        ref="ldap_bind_dn"
        class="field"
        @input="set('ldap_bind_dn', $event.trim())"
      />
      <cv-text-input
        type="password"
        :label="$t('ldap_login.bind_password')"
        :value="value.ldap_bind_password"
        :placeholder="bindPasswordSet ? $t('ldap_login.secret_keep') : ''"
        :helper-text="
          bindPasswordSet
            ? $t('ldap_login.secret_is_set')
            : $t('ldap_login.bind_password_helper')
        "
        :password-hide-label="$t('ldap_login.hide')"
        :password-show-label="$t('ldap_login.show')"
        :invalid-message="errorText('ldap_bind_password')"
        :disabled="disabled"
        ref="ldap_bind_password"
        class="field"
        @input="set('ldap_bind_password', $event)"
      />
      <cv-text-input
        :label="$t('ldap_login.user_attribute')"
        :value="value.ldap_user_attribute"
        :placeholder="
          value.ldap_schema === 'rfc2307' ? 'uid' : 'sAMAccountName'
        "
        :helper-text="$t('ldap_login.user_attribute_helper')"
        :invalid-message="errorText('ldap_user_attribute')"
        :disabled="disabled"
        ref="ldap_user_attribute"
        class="field"
        @input="set('ldap_user_attribute', $event.trim())"
      />
      <cv-text-input
        :label="$t('ldap_login.group')"
        :value="value.ldap_group"
        :helper-text="$t('ldap_login.group_custom_helper')"
        :invalid-message="errorText('ldap_group')"
        :disabled="disabled"
        ref="ldap_group"
        class="field"
        @input="set('ldap_group', $event.trim())"
      />
    </template>
  </div>
</template>

<script>
import to from "await-to-js";
import { mapState } from "vuex";
import { TaskService, UtilService } from "@nethserver/ns8-ui-lib";

let counter = 0;

export const LDAP_FIELDS = [
  "ldap_source",
  "ldap_domain",
  "ldap_group",
  "ldap_url",
  "ldap_start_tls",
  "ldap_tls_verify",
  "ldap_schema",
  "ldap_base_dn",
  "ldap_bind_dn",
  "ldap_bind_password",
  "ldap_user_attribute",
];

/** The ldap_* values of a get-configuration output, ready for v-model. */
export function ldapFromConfiguration(c) {
  const domains = c.user_domains || [];
  return {
    ldap_source: c.ldap_source || (domains.length ? "domain" : "custom"),
    ldap_domain: c.ldap_domain || (domains.length === 1 ? domains[0] : ""),
    ldap_group: c.ldap_group || "",
    ldap_url: c.ldap_url || "",
    ldap_start_tls: !!c.ldap_start_tls,
    ldap_tls_verify: c.ldap_tls_verify !== false,
    ldap_schema: c.ldap_schema || "ad",
    ldap_base_dn: c.ldap_base_dn || "",
    ldap_bind_dn: c.ldap_bind_dn || "",
    ldap_bind_password: "",
    ldap_user_attribute: c.ldap_user_attribute || "",
  };
}

/** Client-side check; returns [field, i18n key] pairs. */
export function validateLdap(v, bindPasswordSet) {
  const errors = [];
  if (v.ldap_source === "domain") {
    if (!v.ldap_domain) errors.push(["ldap_domain", "common.required"]);
  } else {
    if (!/^ldaps?:\/\/[^\s/]+\/?$/.test(v.ldap_url))
      errors.push(["ldap_url", "ldap_login.ldap_url_invalid"]);
    if (!v.ldap_base_dn) errors.push(["ldap_base_dn", "common.required"]);
    if (!v.ldap_bind_dn) errors.push(["ldap_bind_dn", "common.required"]);
    if (!v.ldap_bind_password && !bindPasswordSet)
      errors.push(["ldap_bind_password", "common.required"]);
  }
  return errors;
}

export default {
  name: "LdapLogin",
  mixins: [TaskService, UtilService],
  props: {
    value: { type: Object, required: true },
    userDomains: { type: Array, default: () => [] },
    bindPasswordSet: { type: Boolean, default: false },
    errors: { type: Object, default: () => ({}) },
    disabled: { type: Boolean, default: false },
  },
  data() {
    return { uid: ++counter, groups: [], loadingGroups: false };
  },
  computed: {
    ...mapState(["instanceName", "core"]),
    isLdaps() {
      return /^ldaps:/i.test(this.value.ldap_url || "");
    },
    groupOptions() {
      const names = this.groups.map((g) => g.name);
      // keep a stored group visible even if the list could not be read
      if (this.value.ldap_group && !names.includes(this.value.ldap_group))
        names.unshift(this.value.ldap_group);
      return names.map((n) => {
        const g = this.groups.find((x) => x.name === n);
        return {
          name: n,
          value: n,
          label: g && g.description ? `${n} (${g.description})` : n,
        };
      });
    },
  },
  watch: {
    "value.ldap_domain": {
      immediate: true,
      handler(domain) {
        if (domain && this.value.ldap_source === "domain")
          this.listGroups(domain);
      },
    },
    "value.ldap_source"(source) {
      if (source === "domain" && this.value.ldap_domain && !this.groups.length)
        this.listGroups(this.value.ldap_domain);
    },
  },
  methods: {
    set(field, val) {
      const next = { ...this.value, [field]: val };
      if (field === "ldap_url" && /^ldaps:/i.test(val))
        next.ldap_start_tls = false;
      this.$emit("input", next);
    },
    setDomain(domain) {
      if (domain === this.value.ldap_domain) return;
      this.$emit("input", {
        ...this.value,
        ldap_domain: domain,
        ldap_group: "",
      });
    },
    errorText(field) {
      return this.errors[field] ? this.$t(this.errors[field]) : "";
    },
    focus(field) {
      this.focusElement(field);
    },
    async listGroups(domain) {
      this.loadingGroups = true;
      this.groups = [];
      const taskAction = "list-ldap-groups";
      const eventId = this.getUuid();
      this.core.$root.$once(
        `${taskAction}-aborted-${eventId}`,
        () => (this.loadingGroups = false)
      );
      this.core.$root.$once(
        `${taskAction}-completed-${eventId}`,
        (taskContext, taskResult) => {
          this.loadingGroups = false;
          if (taskContext.data.domain === this.value.ldap_domain)
            this.groups = taskResult.output.groups || [];
        }
      );
      const res = await to(
        this.createModuleTaskForApp(this.instanceName, {
          action: taskAction,
          data: { domain },
          extra: {
            title: this.$t("ldap_login.list_groups"),
            isNotificationHidden: true,
            eventId,
          },
        })
      );
      if (res[0]) this.loadingGroups = false;
    },
  },
};
</script>

<style scoped lang="scss">
@import "../styles/carbon-utils";
.field {
  margin-top: $spacing-06;
}
.ldap-note {
  margin-top: $spacing-03;
  color: #525252;
}
</style>
