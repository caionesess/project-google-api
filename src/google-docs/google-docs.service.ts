import { Injectable, Logger } from '@nestjs/common';
import { ConfigService } from '@nestjs/config';
import { google } from 'googleapis';

@Injectable()
export class GoogleDocsService {
  private readonly logger = new Logger(GoogleDocsService.name);
  private docs: ReturnType<typeof google.docs>;

  constructor(private readonly configService: ConfigService) {
    const credentialsPath = this.configService.get<string>('GOOGLE_APPLICATION_CREDENTIALS');
    
    const authConfig: any = {
      scopes: ['https://www.googleapis.com/auth/documents.readonly'],
    };

    if (credentialsPath) {
      authConfig.keyFile = credentialsPath;
    }

    const auth = new google.auth.GoogleAuth(authConfig);

    this.docs = google.docs({
      version: 'v1',
      auth,
    });
  }

  /**
   * Busca um documento do Google Docs pelo ID e retorna seu conteúdo em HTML
   * @param documentId ID do documento do Google Docs
   * @returns Conteúdo do documento em formato HTML
   */
  async getDocumentAsHtml(documentId: string): Promise<string> {
    try {
      this.logger.log(`Buscando documento: ${documentId}`);

      const response = await this.docs.documents.get({
        documentId,
      });

      const document = response.data;
      if (!document) {
        throw new Error('Documento não encontrado');
      }

      const html = this.convertToHtml(document);
      this.logger.log(`Documento convertido para HTML com sucesso`);

      return html;
    } catch (error: any) {
      this.logger.error(`Erro ao buscar documento: ${error.message}`, error.stack);

      if (error.message?.includes('permission') || error.code === 403) {
        const serviceAccountEmail = await this.getServiceAccountEmail();
        throw new Error(
          `Permissão negada: O documento não foi compartilhado com a Service Account. ` +
          `Compartilhe o documento com o email: ${serviceAccountEmail} ` +
          `com permissão de "Visualizador".`,
        );
      }

      if (error.code === 404) {
        throw new Error(`Documento não encontrado. Verifique se o ID do documento está correto.`);
      }

      throw new Error(`Falha ao buscar documento: ${error.message}`);
    }
  }

  /**
   * Obtém o email da Service Account a partir das credenciais
   * @returns Email da Service Account
   */
  private async getServiceAccountEmail(): Promise<string> {
    try {
      const credentialsPath = this.configService.get<string>('GOOGLE_APPLICATION_CREDENTIALS');
      
      if (credentialsPath) {
        const fs = await import('fs/promises');
        const credentials = JSON.parse(await fs.readFile(credentialsPath, 'utf-8'));
        return credentials.client_email || 'email não encontrado';
      }

      const auth = new google.auth.GoogleAuth();
      const client = await auth.getClient();
      
      if (client && 'email' in client) {
        return (client as any).email || 'email não encontrado';
      }

      return 'email não encontrado';
    } catch (error) {
      this.logger.warn('Não foi possível obter o email da Service Account', error);
      return 'verifique o arquivo de credenciais';
    }
  }

  /**
   * Converte o documento do Google Docs para HTML
   * @param document Documento retornado pela API do Google Docs
   * @returns String HTML formatada
   */
  private convertToHtml(document: any): string {
    const body = document.body?.content || [];
    let html = '<!DOCTYPE html>\n<html>\n<head>\n<meta charset="UTF-8">\n';
    html += `<title>${document.title || 'Documento'}</title>\n`;
    html += '<style>body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; }</style>\n';
    html += '</head>\n<body>\n';

    html += this.processContent(body);

    html += '</body>\n</html>';
    return html;
  }

  /**
   * Processa o conteúdo do documento recursivamente
   * @param content Array de elementos do documento
   * @returns String HTML processada
   */
  private processContent(content: any[]): string {
    let html = '';

    for (const element of content) {
      if (element.paragraph) {
        html += this.processParagraph(element.paragraph);
      } else if (element.table) {
        html += this.processTable(element.table);
      } else if (element.sectionBreak) {
        html += '<hr>\n';
      }
    }

    return html;
  }

  /**
   * Processa um parágrafo do documento
   * @param paragraph Elemento de parágrafo
   * @returns String HTML do parágrafo
   */
  private processParagraph(paragraph: any): string {
    const elements = paragraph.elements || [];
    let text = '';

    for (const elem of elements) {
      if (elem.textRun) {
        text += this.formatTextRun(elem.textRun);
      }
    }

    const style = paragraph.paragraphStyle;
    if (style?.namedStyleType) {
      return this.formatHeading(text, style.namedStyleType);
    }

    if (text.trim()) {
      return `<p>${text}</p>\n`;
    }

    return '<br>\n';
  }

  /**
   * Formata um texto com suas formatações (negrito, itálico, etc)
   * @param textRun Elemento de texto com formatação
   * @returns String HTML formatada
   */
  private formatTextRun(textRun: any): string {
    let text = textRun.content || '';
    const style = textRun.textStyle;

    if (!style) {
      return this.escapeHtml(text);
    }

    text = this.escapeHtml(text);

    if (style.bold) {
      text = `<strong>${text}</strong>`;
    }
    if (style.italic) {
      text = `<em>${text}</em>`;
    }
    if (style.underline) {
      text = `<u>${text}</u>`;
    }
    if (style.strikethrough) {
      text = `<s>${text}</s>`;
    }

    if (style.link?.url) {
      text = `<a href="${style.link.url}">${text}</a>`;
    }

    return text;
  }

  /**
   * Formata cabeçalhos baseado no tipo de estilo
   * @param text Texto do cabeçalho
   * @param styleType Tipo de estilo do Google Docs
   * @returns String HTML do cabeçalho
   */
  private formatHeading(text: string, styleType: string): string {
    const level = this.getHeadingLevel(styleType);
    if (level) {
      return `<h${level}>${text}</h${level}>\n`;
    }
    return `<p>${text}</p>\n`;
  }

  /**
   * Obtém o nível do cabeçalho (1-6) baseado no tipo de estilo
   * @param styleType Tipo de estilo do Google Docs
   * @returns Nível do cabeçalho ou null
   */
  private getHeadingLevel(styleType: string): number | null {
    const headingMap: Record<string, number> = {
      HEADING_1: 1,
      HEADING_2: 2,
      HEADING_3: 3,
      HEADING_4: 4,
      HEADING_5: 5,
      HEADING_6: 6,
    };

    return headingMap[styleType] || null;
  }

  /**
   * Processa uma tabela do documento
   * @param table Elemento de tabela
   * @returns String HTML da tabela
   */
  private processTable(table: any): string {
    const rows = table.tableRows || [];
    let html = '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width: 100%;">\n';

    for (const row of rows) {
      html += '<tr>\n';
      const cells = row.tableCells || [];

      for (const cell of cells) {
        html += '<td>\n';
        html += this.processContent(cell.content || []);
        html += '</td>\n';
      }

      html += '</tr>\n';
    }

    html += '</table>\n';
    return html;
  }

  /**
   * Escapa caracteres HTML especiais
   * @param text Texto a ser escapado
   * @returns Texto escapado
   */
  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }
}

